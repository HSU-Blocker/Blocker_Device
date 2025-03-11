import json
import base64
import os
from ecdsa import SigningKey, VerifyingKey, NIST256p
from charm.toolbox.pairinggroup import PairingGroup

# 전역적으로 PairingGroup 객체 생성
GLOBAL_GROUP = PairingGroup('SS512')

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

    @staticmethod
    def serialize_message(message):
        """메시지 직렬화: JSON 변환 가능하도록 변환"""
        def encode_custom(obj):
            if isinstance(obj, bytes):
                return {"__bytes__": base64.b64encode(obj).decode()}
            elif isinstance(obj, type(GLOBAL_GROUP.random())):  # Element 대신 PairingGroup의 랜덤 요소 타입 확인
                return {"__element__": base64.b64encode(GLOBAL_GROUP.serialize(obj)).decode()}
            elif isinstance(obj, set):  # set을 list로 변환
                return list(obj)
            return obj

        # default=encode_custom을 사용해 변환 시도
        return json.dumps(message, sort_keys=True, default=encode_custom).encode()

    @staticmethod
    def deserialize_message(message_json):
        """메시지 역직렬화: Base64 → bytes 및 PairingGroup 요소 변환"""
        def decode_custom(d):
            if "__bytes__" in d:
                return base64.b64decode(d["__bytes__"])
            elif "__element__" in d:
                return GLOBAL_GROUP.deserialize(base64.b64decode(d["__element__"]))
            return d

        return json.loads(message_json, object_hook=decode_custom)

    # ECDSA를 이용해 um에 대한 서명 생성
    def sign_signature(self, message):
        """메시지를 서명하여 Base64로 인코딩된 서명 값 반환"""
        message_json = self.serialize_message(message)
        signature = self.manufacture_signing_key.sign(message_json)
        return base64.b64encode(signature).decode()

    # ECDSA를 이용해 um에 대한 서명 검증
    def verify_signature(self, message, signature):
        """서명을 검증하여 유효성 여부 반환 (True / False)"""
        message_json = self.serialize_message(message)
        signature_bytes = base64.b64decode(signature)
        try:
            return self.manufacture_verifying_key.verify(signature_bytes, message_json)
        except Exception:
            return False
