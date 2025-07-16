from flask import Flask, request, jsonify
from transformers import pipeline
import requests

app = Flask(__name__)
pipe = pipeline("text-generation", model="distilgpt2", device=-1)
CAR_API_URL = "http://192.168.0.15:8888/command"

@app.route("/llm", methods=["POST"])
def llm():
    user_text = request.json.get("prompt", "")
    # print(f"[llm] Received: {user_text}")

    # 1) LLM으로 텍스트 생성
    result = pipe(user_text, max_new_tokens=20, do_sample=True, truncation=True)
    say_text = result[0]["generated_text"]

    # 2) 생성한 텍스트를 차량에 say 명령으로 전달
    try:
        response = requests.post(CAR_API_URL, json={"command": "say", "text": say_text}, timeout=3)
        print(f"[llm] Sent to car: {say_text}, status: {response.status_code}")
    except Exception as e:
        print(f"[llm] Error sending to car: {e}")

    # 3) JSON 반환
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
