from charm.toolbox.pairinggroup import PairingGroup, GT
from charm.schemes.abenc.abenc_bsw07 import CPabe_BSW07
from charm.core.engine.util import bytesToObject
import os
import json
import logging
import base64

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CPABETools:
    def __init__(self):
        """
        CP-ABE(BSW07) 스킴 초기화 클래스.
        - PairingGroup("SS512")를 사용하여 안전한 암호연산 환경 생성
        - CPabe_BSW07 스킴을 로딩하여 정책 기반 암호화/복호화 기능 사용 가능
        """
        self.group = PairingGroup("SS512")
        self.cpabe = CPabe_BSW07(self.group)
        self.charm_installed = True
        logger.info("Charm-crypto 라이브러리 로드 성공. CP-ABE 기능 활성화됨.")

    def decrypt(self, encrypted_key_json, public_key, device_secret_key):
        """
        암호문(JSON 문자열)을 복호화.
        - 입력: JSON(base64 직렬화된 암호문), 공개키, 디바이스 비밀키
        - base64 → 그룹 원소로 역직렬화한 뒤 복호화 수행
        - 접근 정책 불충족 시 None 반환
        """
        try:
            # JSON 문자열 파싱
            if isinstance(encrypted_key_json, str):
                encrypted_data = json.loads(encrypted_key_json)
            else:
                encrypted_data = encrypted_key_json

            # base64 문자열을 그룹 원소로 변환
            def deserialize_element(obj):
                if isinstance(obj, str):
                    try:
                        return bytesToObject(base64.b64decode(obj), self.group)
                    except Exception:
                        return obj  # 단순 문자열은 그대로 유지
                elif isinstance(obj, list):
                    return [deserialize_element(e) for e in obj]
                elif isinstance(obj, dict):
                    return {k: deserialize_element(v) for k, v in obj.items()}
                else:
                    return obj

            deserialized = deserialize_element(encrypted_data)

            # 복호화 실행
            decrypted_result = self.cpabe.decrypt(public_key, device_secret_key, deserialized)
            if isinstance(decrypted_result, bool):
                logger.error("접근 정책이 충족되지 않음")
                return None
            return decrypted_result
        except Exception as e:
            logger.error(f"CP-ABE 복호화 실패: {e}")
            return None

    def load_public_key(self, public_key_file):
        """
        저장된 공개키(JSON base64)를 로드하여 복원.
        """
        with open(public_key_file, "r") as f:
            serialized_pk = json.load(f)
        pk = {k: bytesToObject(base64.b64decode(v), self.group) for k, v in serialized_pk.items()}
        return pk

    def load_device_secret_key(self, device_secret_key_file):
        """
        저장된 디바이스 비밀키(JSON base64)를 로드하여 복원.
        - 주의: 비밀키 내부에는 'S'라는 속성 리스트가 포함되어 있음
        → 이는 단순 문자열 리스트이므로 base64 decode 하면 오류 발생
        → 따라서 key_name == "S"일 때는 그대로 반환
        """
        with open(device_secret_key_file, "r") as f:
            serialized_key = json.load(f)

        def deserialize_element(obj, key_name=None):
            # 'S' 키는 속성 리스트 → 그대로 문자열 반환
            if key_name == "S":
                return obj

            if isinstance(obj, str):
                try:
                    return bytesToObject(base64.b64decode(obj), self.group)
                except Exception:
                    return obj  # 순수 문자열은 그대로 유지
            elif isinstance(obj, list):
                return [deserialize_element(e, key_name) for e in obj]
            elif isinstance(obj, dict):
                return {k: deserialize_element(v, k) for k, v in obj.items()}
            else:
                return obj

        return deserialize_element(serialized_key)

    def get_group(self):
        """
        PairingGroup 객체 반환 (외부에서 GT 요소 생성 등 활용 가능).
        """
        return self.group