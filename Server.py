import json
import time
import uuid
from flask import Flask, request, jsonify
from openai import OpenAI
import concurrent.futures
import sqlite3
import requests

# server_config.json에서 API 키를 읽어오기
with open('./configs/server_config.json') as config_file:
    config = json.load(config_file)
    openai_api_key = config.get('openai_apiKey')

# Flask 앱 초기화
app = Flask(__name__)
client = OpenAI(api_key=openai_api_key)
client_emote = OpenAI(api_key=openai_api_key)

formatted_functions = []

db_dir = './configs/functions.db'
prompt_dir = './configs/prompts.json'
emotion_prompt_dir = './configs/emotion_prompt.txt'
chat_history_dir = './configs/chat_history.json'

def save_function_to_db(name, description, content):
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    c.execute('INSERT INTO functions (name, description, content, parameter) VALUES (?, ?, ?, ?)', (name, description, content))
    conn.commit()
    conn.close()

def convert_parameters(param_text):
    param_dict = {}
    if param_text:
        params = param_text.split(',')
        for param in params:
            param = param.strip()
            param_parts = param.split()
            if len(param_parts) == 2:
                param_type, param_name = param_parts
                param_dict[param_name] = {"type": param_type}
            elif len(param_parts) == 1:
                param_name = param_parts[0]
                param_dict[param_name] = {"type": "string"}
    return param_dict

def load_functions_from_db():
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    c.execute('SELECT name, description, content, parameter FROM functions')
    functions = c.fetchall()
    conn.close()

    for func in functions:
        parameters = {}
        if func[3] != "":
            parameters = convert_parameters(func[3])
        #print(parameters)
        function_info = {
            "name": func[0],
            "description": func[1],
            "parameters": {
                "type": "object",
                "properties": convert_parameters(func[3])
            }
        }
        formatted_functions.append(function_info)

    return functions

def find_function_in_db(function_name):
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    c.execute('SELECT content FROM functions WHERE name = ?', (function_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def print_functions_from_db():
    conn = sqlite3.connect(db_dir)
    c = conn.cursor()
    try:
        c.execute('SELECT name, description, content, parameter FROM functions')
    except sqlite3.OperationalError as e:
        if "no such column: parameter" in str(e):
            c.execute('SELECT name, description, content FROM functions')
            functions = c.fetchall()
            conn.close()
        else:
            conn.close()
            print(f"Error: {e}")
            return
    else:
        functions = c.fetchall()
        conn.close()

def findfunction(function_name, *args):
    content = find_function_in_db(function_name)
    
    # 첫 번째 인수는 JSON 문자열이라 가정
    json_str = args[0]
    args_dict = json.loads(json_str)
    args_list = list(args_dict.values())
    
    # 적절한 형식으로 함수 호출 부분을 생성
    function_call = f"result = {function_name}(*{args_list})"
    
    print(content)
    print(function_call, args_list)
    
    try:
        local_namespace = {}
        # 먼저 함수 정의 부분을 실행
        exec(content, globals(), local_namespace)
        # 그 다음 함수 호출 부분을 실행
        exec(function_call, globals(), local_namespace)
        result = "네, 주인님! " + function_name + "을 실행하였습니다! 결과는 " + str(local_namespace["result"]) + "에요"
    except Exception as e:        
        result = "명령을 처리하는데 실패하였습니다. "
        print(e)
    
    print(result)
    return result

def analyze_emotion(text):

    with open(emotion_prompt_dir, 'r', encoding='utf-8') as file:
        emotion_prompt = json.load(file)

    response = client_emote.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"{emotion_prompt}"},
            {"role": "user", "content": f"{text}"}
        ],
        max_tokens=20,
        temperature=0.1
    )
    emotion = response.choices[0].message.content
    return emotion

@app.route("/kakaoTalk", methods=["POST"])
def kakao_talk():
    body = request.get_json()
    print(body)
    print(body['userRequest']['utterance'])

    payload = {
        "say": body['userRequest']['utterance']
    }
    
    response_say = call_gpt_chat(payload).get_json()["say"] 

    responseBody = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": response_say
                    }
                }
            ]
        }
    }
    return responseBody

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route('/api/callGPTChat/', methods=['POST'])
def call_gpt_chat(insertData=None):
    if insertData is not None:
        data = insertData
    else:
        data = request.json

    with open(prompt_dir, 'r', encoding='utf-8') as file:
        prompt_data = json.load(file)
    
    system_prompt = prompt_data.get('system', '')
    character_prompt = prompt_data.get('character', '')
    command_prompt = prompt_data.get('command', '')
    
    full_prompt = f"{system_prompt}\n{character_prompt}\n{command_prompt}"
    
    print(data["say"])
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": data["say"]}
        ],
        max_tokens=256,
        temperature=0.9,
        functions=formatted_functions,
        function_call="auto"
    )

    # function call 응답 처리
    ai_response = response.choices[0]
    if ai_response.finish_reason == "function_call":
        function_name = ai_response.message.function_call.name
        result = findfunction(function_name, ai_response.message.function_call.arguments)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": data["say"] + result}
            ],
            max_tokens=256,
            temperature=0.9
        )
        ai_response = response.choices[0]
        
    say_content = ai_response.message.content
    print(say_content)
    emotion = analyze_emotion(say_content)
    
    result = {
        "say": say_content,
        "reaction": emotion
    }
    print(result)

    # 채팅 내역을 JSON 파일에 기록
    chat_entry = {
        "user": data['say'],
        "ai": result['say'],
        "positive": None
    }
    try:
        with open(chat_history_dir, 'r', encoding='utf-8') as file:
            chat_history = json.load(file)
    except FileNotFoundError:
        chat_history = []

    chat_history.append(chat_entry)

    with open(chat_history_dir, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)

    return jsonify(result)

# @app.route('/api/stt', methods=['POST'])
# def SpeechToText():
#     # Get the file from the request
#     if 'file' not in request.files:
#         return jsonify({"error": "No file part"}), 400

#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     file_path = './audio/received_audio.wav'
#     file.save(file_path)

#     # OpenAI Whisper API call
#     with open(file_path, 'rb') as audio:
#         response = client.audio.transcriptions.create(
#             model="whisper-1",
#             file=audio, 
#             response_format="text",
#             language="ko"  # Specify Korean language
#         )
#     print("stt 결과 ")
#     print(response)
#     return jsonify({"transcription": response}), 200

if __name__ == '__main__':
    load_functions_from_db()
    app.run(host='0.0.0.0', port=80)



