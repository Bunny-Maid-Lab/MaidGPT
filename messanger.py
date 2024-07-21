import sys
import json
import os
import requests
import time
import wave
import pyaudio
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QCheckBox, QLabel
)
from PyQt5.QtGui import QPixmap, QPalette, QBrush
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Constants for audio recording
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
THRESHOLD = 5000  # Adjust this threshold based on your environment
SILENCE_DURATION = 0.5  # Duration in seconds to wait before considering silence
STREAM_RESET_INTERVAL = 10 * 60  # 10 minutes

class AudioRecorder(QThread):
    audio_data_ready = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.audio_frames = []
        self.active_frames = []
        self.p = pyaudio.PyAudio()
        self.silence_timer = None

    def run(self):
        self.record_audio()

    def record_audio(self):
        def open_audio_stream():
            return self.p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
        
        audio_stream = open_audio_stream()

        self.silence_timer = None
        self.audio_frames = []
        self.active_frames = []
        self.is_recording = True
        recording = False  # 추가된 부분: 실제 녹음 시작 여부
        last_reset_time = time.time()  # 스트림 초기화 시간 기록

        while self.is_recording:
            if time.time() - last_reset_time > STREAM_RESET_INTERVAL:
                audio_stream.stop_stream()
                audio_stream.close()
                audio_stream = open_audio_stream()
                last_reset_time = time.time()

            data = audio_stream.read(CHUNK)

            # Volume analysis
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.linalg.norm(audio_data)

            if volume > THRESHOLD:
                if not recording:
                    recording = True  # 녹음 시작
                    self.active_frames = []  # 기존 데이터 삭제
                self.active_frames.append(data)
                self.silence_timer = None
            else:
                if recording:
                    if self.silence_timer is None:
                        self.silence_timer = time.time()
                    elif time.time() - self.silence_timer > SILENCE_DURATION:
                        self.audio_data_ready.emit(b''.join(self.active_frames))
                        self.active_frames = []
                        recording = False
                        self.silence_timer = None

        audio_stream.stop_stream()
        audio_stream.close()

    def save_audio(self, frames):
        wf = wave.open('./audio/output.wav', 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def stop(self):
        self.is_recording = False
        self.quit()
        self.wait()

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.stt_enabled = False
        self.tts_enabled = False
        self.server_ip = None

        self.initUI()
        self.load_chat_history()

        self.audio_recorder = AudioRecorder()
        self.audio_recorder.audio_data_ready.connect(self.handle_stt_result)

    def initUI(self):
        self.setWindowTitle("Chat Program")

        # Create main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # IP input layout
        self.ip_input_layout = QHBoxLayout()
        self.layout.addLayout(self.ip_input_layout)

        # IP input
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter server IP address")
        self.ip_input_layout.addWidget(self.ip_input)
        self.ip_input.setText("127.0.0.1")

        # Add image at the top
        self.image_label = QLabel()
        self.image_label.setPixmap(QPixmap("./static/Hana.png"))
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        # Chat history display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: rgba(192, 192, 192, 180); color: black;")  # Semi-transparent gray with black text
        self.layout.addWidget(self.chat_display)

        # Input layout
        self.input_layout = QHBoxLayout()
        self.layout.addLayout(self.input_layout)

        # Message input
        self.message_input = QLineEdit()
        self.message_input.setStyleSheet("color: black;")  # Black text color for the input
        self.message_input.returnPressed.connect(self.send_message)
        self.input_layout.addWidget(self.message_input)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        # STT and TTS checkboxes
        self.stt_checkbox = QCheckBox("STT")
        self.stt_checkbox.setStyleSheet("color: black;")  # Set text color to black
        self.stt_checkbox.stateChanged.connect(self.toggle_stt)
        self.input_layout.addWidget(self.stt_checkbox)

        self.tts_checkbox = QCheckBox("TTS")
        self.tts_checkbox.setStyleSheet("color: black;")  # Set text color to black
        self.tts_checkbox.stateChanged.connect(self.toggle_tts)
        self.input_layout.addWidget(self.tts_checkbox)

        self.show()

    def set_background_image(self, image_path):
        background_image = QPixmap(image_path)
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(background_image))
        self.setPalette(palette)

    def load_chat_history(self):
        if os.path.exists('./configs/chat_history.json'):
            with open('./configs/chat_history.json', 'r', encoding='utf-8') as file:
                try:
                    chat_history = json.load(file)
                    for entry in chat_history:
                        user_message = entry.get("user", "")
                        ai_message = entry.get("ai", "")
                        if user_message:
                            self.chat_display.append(f"User: {user_message}")
                        if ai_message:
                            self.chat_display.append(f"AI: {ai_message}")
                except json.JSONDecodeError:
                    print("Error decoding JSON")

    def save_chat_history(self):
        chat_history = []
        chat_lines = self.chat_display.toPlainText().split('\n')
        for i in range(0, len(chat_lines), 2):
            if i+1 < len(chat_lines):
                user_message = chat_lines[i].replace("User: ", "").strip()
                ai_message = chat_lines[i+1].replace("AI: ", "").strip()
                chat_history.append({"user": user_message, "ai": ai_message})
        with open('./configs/chat_history.json', 'w', encoding='utf-8') as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)

    def send_message(self):
        message = self.message_input.text()
        self.server_ip = self.ip_input.text().strip()
        if message and self.server_ip:
            self.chat_display.append(f"User: {message}")
            self.message_input.clear()

            # Prepare the JSON data
            data = {
                "say": message
            }

            # Send the POST request
            try:
                response = requests.post(f"http://{self.server_ip}:80/api/callGPTChat", json=data)
                if response.status_code == 200:
                    ai_response = response.json().get("say")
                    self.chat_display.append(f"AI: {ai_response}")
                    
                    # TTS 처리
                    if self.tts_enabled:
                        self.handle_tts_request(response.json())
                else:
                    self.chat_display.append(f"AI: Error {response.status_code}")
            except requests.RequestException as e:
                self.chat_display.append(f"AI: Request failed ({e})")

            self.save_chat_history()

    def handle_stt_result(self, audio_data):
        self.server_ip = self.ip_input.text().strip()
        if self.server_ip:
            # wave 파일로 저장
            with wave.open('./audio/output.wav', 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(audio_data)
                
            files = {'file': ('./audio/output.wav', open('./audio/output.wav', 'rb'), 'audio/wav')}
            try:
                response = requests.post(f"http://{self.server_ip}:6008/api/stt", files=files)
                if response.status_code == 200:
                    stt_response = response.json().get("transcription")
                    print(stt_response)
                    self.message_input.setText(stt_response)
                    self.send_message()
                else:
                    self.chat_display.append(f"STT: Error {response.status_code}")
            except requests.RequestException as e:
                self.chat_display.append(f"STT: Request failed ({e})")

    def handle_tts_request(self, data):
        if self.server_ip:
            try:
                data['speaker'] = 33
                response = requests.post(f"http://{self.server_ip}:6007/tts", json=data)
                if response.status_code == 200:
                    with open('./audio/tts_output.wav', 'wb') as f:
                        f.write(response.content)
                    self.play_audio('./audio/tts_output.wav')
                else:
                    self.chat_display.append(f"TTS: Error {response.status_code}")
            except requests.RequestException as e:
                self.chat_display.append(f"TTS: Request failed ({e})")

    def toggle_stt(self, state):
        self.stt_enabled = state == Qt.Checked
        if self.stt_enabled:
            self.audio_recorder.start()
        else:
            self.audio_recorder.stop()
        print(f"STT enabled: {self.stt_enabled}")

    def toggle_tts(self, state):
        self.tts_enabled = state == Qt.Checked
        print(f"TTS enabled: {self.tts_enabled}")

    def play_audio(self, file_path):
        chunk = 1024
        wf = wave.open(file_path, 'rb')
        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        data = wf.readframes(chunk)

        while data:
            stream.write(data)
            data = wf.readframes(chunk)

        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatWindow()
    sys.exit(app.exec_())
