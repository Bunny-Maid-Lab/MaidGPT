from flask import Flask, request, jsonify
import os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import json
from openai import OpenAI

# server_config.json에서 API 키를 읽어오기
with open('./configs/server_config.json') as config_file:
    config = json.load(config_file)
    openai_api_key = config.get('openai_apiKey')

# Flask 앱 초기화
app = Flask(__name__)
client = OpenAI(api_key=openai_api_key)
client_emote = OpenAI(api_key=openai_api_key)

# 디바이스 설정 (GPU가 없는 경우 CPU로 설정)
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

# 모델과 프로세서 로드
model_id = "openai/whisper-large-v3"

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)
model.to(device)

processor = AutoProcessor.from_pretrained(model_id)

# 한국어로 강제 설정
forced_decoder_ids = processor.tokenizer.convert_tokens_to_ids(["<|ko|>", "<|transcribe|>", "<|notimestamps|>"])
model.config.forced_decoder_ids = [(1, forced_decoder_ids[0]), (2, forced_decoder_ids[1]), (3, forced_decoder_ids[2])]

pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    max_new_tokens=128,
    chunk_length_s=30,
    batch_size=16,
    return_timestamps=True,
    torch_dtype=torch_dtype,
    device=device,
)

# Local STT 
# @app.route('/api/stt', methods=['POST'])
# def SpeechToText():
#     # 요청에서 파일 가져오기
#     if 'file' not in request.files:
#         return jsonify({"error": "No file part"}), 400

#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({"error": "No selected file"}), 400

#     # 파일 저장 경로 설정
#     file_path = './audio/received_audio.wav'
#     os.makedirs(os.path.dirname(file_path), exist_ok=True)
#     file.save(file_path)

#     try:
#         # 음성 파일을 모델에 입력하여 텍스트 변환
#         result = pipe(file_path)
#         transcription = result["text"]

#         return jsonify({"transcription": transcription}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# OpenAI STT
@app.route('/api/stt', methods=['POST'])
def SpeechToText():
    # Get the file from the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = './audio/received_audio.wav'
    file.save(file_path)

    # OpenAI Whisper API call
    with open(file_path, 'rb') as audio:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio, 
            response_format="text",
            language="ko"  # Specify Korean language
        )
    print("stt 결과 ")
    print(response)
    return jsonify({"transcription": response}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6008)