from flask import Flask, jsonify, request, redirect, url_for, render_template, session, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from cryptography.fernet import Fernet
import numpy as np
import os
import subprocess
import json
import re
import requests
import sqlite3
import pyaudio
import wave
import threading
import time
import hashlib
import io
from functools import wraps
import secrets

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key =  # 세션을 위한 비밀 키 설정
CORS(app)

# 녹음 설정
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
THRESHOLD = 8000  # 음량 크기 기준 설정
SILENCE_DURATION = 1  # 1초 동안 음량이 기준 이하일 때 녹음 중지

is_recording = False
audio_frames = []
audio_stream = None
p = pyaudio.PyAudio()
silence_timer = None

# Server.py를 백그라운드에서 실행
hana_server_process = subprocess.Popen(["python", "Server.py"])
tts_server_process = subprocess.Popen(["python", "./WhisperSTT/whisper_Server.py"])
stt_server_process = subprocess.Popen(["python", "./MeloTTS/tts_server.py"])
db_dir = './configs/functions.db'

# JSON 파일에서 데이터 로드
with open('./configs/server_config.json') as config_file:
    config = json.load(config_file)

# 사용자 인증 정보
USERNAME = config.get('USERNAME')
PASSWORD = config.get('PASSWORD')

server_ip = config.get('server_ip')

prompt_file_path = './configs/prompts.json'
chat_history_dir = './configs/chat_history.json'
emotion_prompt_dir = './configs/emotion_prompt.txt'

# 파일이 없거나 비어있으면 기본값으로 파일 생성
if not os.path.exists(prompt_file_path) or os.stat(prompt_file_path).st_size == 0:
    prompt_data = {
        'system': '',
        'character': '',
        'command': ''
    }
    with open(prompt_file_path, 'w', encoding='utf-8') as file:
        json.dump(prompt_data, file)
else:
    with open(prompt_file_path, 'r', encoding='utf-8') as file:
        prompt_data = json.load(file)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    try:
        response = requests.get(f"http://{server_ip}:80/health")
        if response.status_code == 200:
            return jsonify({"status": "healthy"})
        else:
            return jsonify({"status": "unhealthy"}), 500
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

def check_auth(username, password):
    """사용자 인증 정보 확인"""
    #return username == USERNAME and password == PASSWORD
    input_hashed_username = hashlib.sha512(username.encode()).hexdigest()
    input_hashed_password = hashlib.sha512(password.encode()).hexdigest()

    return input_hashed_username == USERNAME and input_hashed_password == PASSWORD
    
def record_audio():
    global audio_frames, active_frames, is_recording, audio_stream, silence_timer

    audio_stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)

    silence_timer = None
    audio_frames = []
    active_frames = []
    start_time = time.time()

    while is_recording:
        data = audio_stream.read(CHUNK)
        audio_frames.append(data)

        # 음량 분석
        audio_data = np.frombuffer(data, dtype=np.int16)
        volume = np.linalg.norm(audio_data)
        #print(f"Volume: {volume}")

        if volume > THRESHOLD:
            active_frames.extend(audio_frames)
            audio_frames = []
            silence_timer = None
        else:
            if silence_timer is None:
                silence_timer = time.time()
            elif time.time() - silence_timer > SILENCE_DURATION:
                if active_frames:
                    save_audio(active_frames)
                    active_frames = []
                    silence_timer = None

    audio_stream.stop_stream()
    audio_stream.close()

def save_audio(frames):
    if not os.path.exists('./audio'):
        os.makedirs('./audio')
    
    timestamp = int(time.time())
    filename = f'./audio/received_audio.wav'
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)  # 예시로 2로 설정, 실제로는 FORMAT에 맞게 설정하세요
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f'Saved {filename}')

    # 파일 저장 후 지정된 URL 호출
    with open(filename, 'rb') as f:
        files = {'file': f}
        response = requests.post(f'http://{server_ip}:80/api/stt', files=files)
    
    if response.status_code == 200:
        transcription = response.json().get('transcription')
        send_transcription_to_client(transcription)
    else:
        print('Failed to get transcription')

def send_transcription_to_client(transcription):
    # 클라이언트로 전송
    socketio.emit('transcription', {'transcription': transcription})

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global is_recording

    if not is_recording:
        is_recording = True
        record_thread = threading.Thread(target=record_audio)
        record_thread.start()
        return jsonify({"status": "recording started"})
    else:
        return jsonify({"status": "already recording"})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global is_recording

    if is_recording:
        is_recording = False
        return jsonify({"status": "recording stopped"})
    else:
        return jsonify({"status": "not recording"})

@app.route('/get_emotion_prompt', methods=['GET'])
def get_emotion_prompt():
    try:
        with open(emotion_prompt_dir, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            'prompt': 'emotion_prompt',
            'emotions': []
        }
    return jsonify(data)

@app.route('/save_emotion_prompt', methods=['POST'])
def save_emotion_prompt():
    data = request.data.decode('utf-8')
    with open(emotion_prompt_dir, 'w', encoding='utf-8') as file:
        file.write(data)
    return jsonify({'status': 'success'})

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_auth(username, password):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid Credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Home page
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# Endpoint to get chat history
@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    with open(chat_history_dir, 'r', encoding='utf-8') as file:
        chat_history = json.load(file)
    return jsonify({"chat_history": chat_history})

@app.route('/update_chat_history', methods=['POST'])
def update_chat_history():
    data = request.json
    with open(chat_history_dir, 'r', encoding='utf-8') as file:
        chat_history = json.load(file)
    for entry in chat_history:
        if entry["user"] == data["user"] and entry["ai"] == data["ai"]:
            entry["positive"] = data["positive"]
            break
    with open(chat_history_dir, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)
    return jsonify({"status": "success"})


@app.route('/get_prompt', methods=['GET'])
def get_prompt():
    return jsonify({
        'system': prompt_data.get('system', ''),
        'character': prompt_data.get('character', ''),
        'command': prompt_data.get('command', '')
    })

@app.route('/save_prompt', methods=['POST'])
def save_prompt():
    data = request.json
    prompt_data['system'] = data['system']
    prompt_data['character'] = data['character']
    prompt_data['command'] = data['command']
    with open(prompt_file_path, 'w') as f:
        json.dump(prompt_data, f)
    return jsonify({'status': 'success'})
    

@app.route('/get_functions', methods=['GET'])
def get_functions():
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    
    # Parameter column 존재 여부 확인
    c.execute("PRAGMA table_info(functions)")
    columns = [info[1] for info in c.fetchall()]
    parameter_exists = 'parameter' in columns

    if parameter_exists:
        c.execute('SELECT name, description, content, parameter FROM functions')
    else:
        c.execute('SELECT name, description, content FROM functions')
        
    functions = c.fetchall()
    conn.close()

    functions_list = []
    for func in functions:
        function_info = {
            "name": func[0],
            "description": func[1],
            "content": func[2]
        }
        if parameter_exists:
            function_info["parameter"] = func[3]
        else:
            function_info["parameter"] = ""
        functions_list.append(function_info)

    print(functions_list)
    return jsonify({"functions": functions_list})

# Endpoint to save functions to Server.py
@app.route('/save_functions', methods=['POST'])
def save_functions():
    data = request.json
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()

    # Parameter column 존재 여부 확인 및 없으면 추가
    c.execute("PRAGMA table_info(functions)")
    columns = [info[1] for info in c.fetchall()]
    if 'parameter' not in columns:
        c.execute("ALTER TABLE functions ADD COLUMN parameter TEXT")

    for func in data['functions']:
        name = func['name']
        description = func['description']
        content = func['content']
        parameter = func.get('parameter', '')

        # 중복 확인 및 업데이트
        c.execute('SELECT COUNT(*) FROM functions WHERE name = ?', (name,))
        count = c.fetchone()[0]
        if count > 0:
            c.execute('UPDATE functions SET description = ?, content = ?, parameter = ? WHERE name = ?', (description, content, parameter, name))
        else:
            c.execute('INSERT INTO functions (name, description, content, parameter) VALUES (?, ?, ?, ?)', (name, description, content, parameter))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/delete_function/<string:name>', methods=['DELETE'])
def delete_function(name):
    conn = sqlite3.connect(db_dir)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM functions WHERE name = ?", (name,))
    conn.commit()
    if cursor.rowcount > 0:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), 404

# Endpoint to restart the server
@app.route('/restart_server', methods=['POST'])
def restart_server():
    global hana_server_process
    hana_server_process.terminate()  # 기존 프로세스 종료
    hana_server_process = subprocess.Popen(["python", "Server.py"])  # 새로운 프로세스 시작
    return jsonify({"status": "restarting"})

def extract_functions(content):
    pattern = re.compile(r'(def\s+(?!analyze_emotion|kakao_talk|call_gpt_chat)\w+\s*\(.*?\)\s*:[\s\S]+?)(?=def\s+\w+\s*\(.*?\)\s*:|$)')
    functions = pattern.findall(content)
    return functions

def update_functions(content, functions):
    parts = content.split('thinqClient = LGClient.client_set()')
    header = parts[0] + 'thinqClient = LGClient.client_set()'
    footer = parts[1].split('def analyze_emotion(text):')[1]
    updated_content = header + '\n\n' + '\n\n'.join(functions) + '\n\ndef analyze_emotion(text):' + footer
    return updated_content

@app.route('/proxy/callGPTChat', methods=['POST'])
def proxy_call_gpt_chat():
    data = request.json
    response = requests.post(f'http://{server_ip}:80/api/callGPTChat/', json=data)
    return jsonify(response.json())

@app.route('/proxy/callGPTChatWithTTS', methods=['POST'])
def proxy_call_gpt_chat_with_TTS():
    data = request.json
    response = requests.post(f'http://{server_ip}:80/api/callGPTChat/', json=data)
    
    if response.status_code == 200:
        response_wav = requests.post(f'http://{server_ip}:5000/tts', json=response.json())
        if response_wav.headers.get('Content-Type') == 'audio/wav':
            return send_file(
                io.BytesIO(response_wav.content),
                mimetype='audio/wav',
                as_attachment=True,
                download_name='response.wav'
            )
        else:
            return jsonify(response.json())
    
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6006)
