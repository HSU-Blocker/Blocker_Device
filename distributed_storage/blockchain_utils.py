import json
import requests

BLOCKCHAIN_API_URL = ""

# 업데이트 메시지(μm)와 서명을 블록체인에 저장
def upload_to_blockchain(data):
    response = requests.post(BLOCKCHAIN_API_URL, json=data)
    if response.status_code == 200:
        return response.json()  # 트랜잭션 해시 반환
    else:
        raise Exception(f"블록체인 업로드 실패: {response.text}")
