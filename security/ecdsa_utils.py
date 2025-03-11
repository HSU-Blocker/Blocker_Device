import json
import base64
import os
from ecdsa import SigningKey, VerifyingKey, NIST256p

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
            print("✅ 제조사 Skmi, Pkmi 로드 완료")
        except FileNotFoundError:
            print("❌ 제조사 키 파일이 존재하지 않습니다.")
            exit()

    def serialize_message(self, message):
        """JSON 직렬화를 위한 Base64 변환 함수"""
        def encode_bytes(obj):
            if isinstance(obj, bytes):
                return base64.b64encode(obj).decode()  # ✅ `bytes` → `Base64 str`
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        return json.dumps(message, sort_keys=True, default=encode_bytes).encode()  # ✅ JSON 변환 후 bytes로 변환

    def deserialize_message(self, message_json):
        """JSON 역직렬화 (Base64 → bytes 변환)"""
        def decode_bytes(obj):
            if isinstance(obj, str):  # Base64로 변환된 값이면 디코딩 시도
                try:
                    return base64.b64decode(obj)  # `Base64 str` → `bytes`
                except Exception:
                    return obj  # 변환 불가능한 경우 원래 str 그대로 반환
            return obj

        return json.loads(message_json, object_hook=lambda d: {k: decode_bytes(v) for k, v in d.items()})

    # ECDSA 서명 (Base64 변환 적용)
    def sign_message(self, message):
        """메시지를 서명하여 Base64로 인코딩된 서명 값 반환"""
        message_json = self.serialize_message(message)  # Base64 변환 후 직렬화
        signature = self.manufacture_signing_key.sign(message_json)  # ECDSA 서명
        return base64.b64encode(signature).decode()  # Base64 인코딩

    # ECDSA 서명 검증 (Base64 디코딩 포함)
    def verify_signature(self, message, signature):
        """서명을 검증하여 유효성 여부 반환 (True / False)"""
        message_json = self.serialize_message(message)  # 직렬화
        signature_bytes = base64.b64decode(signature)  # Base64 디코딩
        try:
            return self.manufacture_verifying_key.verify(signature_bytes, message_json)  # 서명 검증
        except Exception:
            return False
