from charm.toolbox.pairinggroup import PairingGroup, GT
from charm.core.engine.util import objectToBytes, bytesToObject
from charm.schemes.abenc.abenc_bsw07 import CPabe_BSW07
import os
import json
import logging
import pickle
from base64 import b64encode, b64decode
from hashlib import sha256
import base64

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CPABETools:
    def __init__(self):
        self.group = PairingGroup("SS512")
        self.cpabe = CPabe_BSW07(self.group)
        self.charm_installed = True
        logger.info("Charm-crypto 라이브러리 로드 성공. CP-ABE 기능 활성화됨.")

    def decrypt(self, encrypted_key_json, public_key, device_secret_key):
        try:
            if isinstance(encrypted_key_json, str):
                encrypted_data = json.loads(encrypted_key_json)
            else:
                encrypted_data = encrypted_key_json

            def deserialize_element(obj):
                if isinstance(obj, str):
                    try:
                        return self.group.deserialize(b64decode(obj))
                    except:
                        return obj
                elif isinstance(obj, list):
                    return [deserialize_element(e) for e in obj]
                elif isinstance(obj, dict):
                    return {k: deserialize_element(v) for k, v in obj.items()}
                else:
                    return obj

            deserialized = deserialize_element(encrypted_data)
            decrypted_result = self.cpabe.decrypt(public_key, device_secret_key, deserialized)
            if isinstance(decrypted_result, bool):
                logger.error("접근 정책이 충족되지 않음")
                return None
            return decrypted_result
        except Exception as e:
            logger.error(f"CP-ABE 복호화 실패: {e}")
            return None

    def load_public_key(self, public_key_file):
        with open(public_key_file, "r") as f:
            serialized_pk = json.load(f)
        pk = {k: self.group.deserialize(v.encode("latin1")) for k, v in serialized_pk.items()}
        return pk

    def load_device_secret_key(self, device_secret_key_file):
        with open(device_secret_key_file, "rb") as f:
            serialized_key = pickle.load(f)

        def deserialize_element(obj):
            if isinstance(obj, bytes):
                return self.group.deserialize(obj)
            elif isinstance(obj, list):
                return [deserialize_element(e) for e in obj]
            elif isinstance(obj, dict):
                return {k: deserialize_element(v) for k, v in obj.items()}
            else:
                return obj

        return deserialize_element(serialized_key)

    def get_group(self):
        return self.group