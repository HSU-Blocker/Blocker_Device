from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import os
import requests
import logging

# 설정
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
CAR_API_URL = "http://192.168.0.15:8888/command"
HF_TOKEN = os.getenv("HF_TOKEN")  # 환경변수에서 토큰 읽기

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 모델 로딩
logger.info("[llm] Loading tokenizer and model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_auth_token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, use_auth_token=HF_TOKEN)
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device=-1)
logger.info("[llm] Model loaded successfully")

# Flask 앱 시작
app = Flask(__name__)

@app.route("/llm", methods=["POST"])
def llm():
    user_text = request.json.get("prompt", "")
    logger.info(f"[llm] Received prompt: {user_text}")

    # 프롬프트 구성 (챗 형식 유지)
    prompt = f"<|user|>\n{user_text}\n<|assistant|>\n"

    # 텍스트 생성
    result = pipe(prompt, max_new_tokens=40, do_sample=True, temperature=0.7, top_p=0.9)
    full_text = result[0]["generated_text"]
    logger.info(f"[llm] Full response: {full_text}")

    # 답변 부분만 추출
    say_text = full_text.split("<|assistant|>\n")[-1].strip()
    logger.info(f"[llm] Final response: {say_text}")

    # # 차량에 전송
    # try:
    #     res = requests.post(CAR_API_URL, json={"command": "say", "text": say_text}, timeout=3)
    #     logger.info(f"[llm] Sent to car, status: {res.status_code}")
    # except Exception as e:
    #     logger.error(f"[llm] Error sending to car: {e}")

    # return jsonify({
    #     "prompt": user_text,
    #     "response": say_text
    # })
    return jsonify({"response": say_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
