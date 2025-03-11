import json
import base64
import os
from ecdsa import SigningKey, VerifyingKey, NIST256p
import keygen

class ECDSAUtils:
    def __init__(self, manufacture_private_key_path, manufacture_public_key_path):
        """
        - manufacture_private_key_path: 제조사 개인 키 파일 경로 (SKmi)
        - manufacture_public_key_path: 제조사 공개 키 파일 경로 (PKmi)
        """
        self.manufacture_private_key_path = manufacture_private_key_path
        self.manufacture_public_key_path = manufacture_public_key_path

        # 키 로드 또는 생성
        self.load_keys()

    def load_keys(self):
        """제조사 개인 키 및 공개 키를 파일에서 로드"""
        try:
            with open(self.manufacture_private_key_path, "rb") as f:
                self.manufacture_signing_key = SigningKey.from_pem(f.read())
            with open(self.manufacture_public_key_path, "rb") as f:
                self.manufacture_verifying_key = VerifyingKey.from_pem(f.read())
            print("제조사 Skmi, Pkmi 로드 완료")
        except FileNotFoundError:
            print("제조사 키 파일이 존재하지 않습니다.")
            exit()

    # ECDSA 서명
    def sign_message(self, message):
        """메시지를 서명하여 Base64로 인코딩된 서명 값 반환"""
        message_json = json.dumps(message, sort_keys=True).encode()
        signature = self.manufacture_signing_key.sign(message_json)
        return base64.b64encode(signature).decode()

    # ECDSA 서명 검증
    def verify_signature(self, message, signature):
        """서명을 검증하여 유효성 여부 반환 (True / False)"""
        message_json = json.dumps(message, sort_keys=True).encode()
        signature_bytes = base64.b64decode(signature)
        try:
            return self.manufacture_verifying_key.verify(signature_bytes, message_json)
        except Exception:
            return False
