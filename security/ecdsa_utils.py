import json
import base64
import os
from ecdsa import SigningKey, VerifyingKey, NIST256p

class ECDSAUtils:
    def __init__(self, private_key_path="private_key.pem", public_key_path="public_key.pem", generate_new=False):
        """
        - private_key_path: 개인 키 파일 경로 (기본값: private_key.pem)
        - public_key_path: 공개 키 파일 경로 (기본값: public_key.pem)
        - generate_new: True이면 새 키 쌍을 생성하여 저장
        """
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path

        # generate_new=True이면 새 키 생성
        if generate_new:
            self.generate_and_save_keys()
        else:
            # 기존 키 로드 또는 자동 생성
            self.load_or_create_keys()

    def generate_and_save_keys(self):
        """새로운 키 쌍을 생성하고 저장"""
        self.signing_key = SigningKey.generate(curve=NIST256p)
        self.verifying_key = self.signing_key.verifying_key
        self.save_keys()
        print("새로운 ECDSA 키 쌍이 생성되었습니다.")

    def save_keys(self):
        """현재 키를 PEM 파일로 저장"""
        with open(self.private_key_path, "wb") as f:
            f.write(self.signing_key.to_pem())
        with open(self.public_key_path, "wb") as f:
            f.write(self.verifying_key.to_pem())
        print(f"📁 키 저장 완료: {self.private_key_path}, {self.public_key_path}")

    def load_or_create_keys(self):
        """키를 로드하거나 없으면 자동 생성"""
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
            self.load_keys()
        else:
            print("키 파일이 없습니다. 새로운 키를 생성합니다.")
            self.generate_and_save_keys()

    def load_keys(self):
        """개인 키 및 공개 키를 파일에서 로드"""
        try:
            with open(self.private_key_path, "rb") as f:
                self.signing_key = SigningKey.from_pem(f.read())
            with open(self.public_key_path, "rb") as f:
                self.verifying_key = VerifyingKey.from_pem(f.read())
            print("기존 키 로드 완료")
        except FileNotFoundError:
            print("키 파일이 존재하지 않습니다. 새로운 키를 생성합니다.")
            self.generate_and_save_keys()

    # ECDSA 서명
    def sign_message(self, message):
        """메시지를 서명하여 Base64로 인코딩된 서명 값 반환"""
        message_json = json.dumps(message, sort_keys=True).encode()
        signature = self.signing_key.sign(message_json)
        return base64.b64encode(signature).decode()

    # ECDSA 서명 검증
    def verify_signature(self, message, signature):
        """서명을 검증하여 유효성 여부 반환 (True / False)"""
        message_json = json.dumps(message, sort_keys=True).encode()
        signature_bytes = base64.b64decode(signature)
        try:
            return self.verifying_key.verify(signature_bytes, message_json)
        except Exception:
            return False
