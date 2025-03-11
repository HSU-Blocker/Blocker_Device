import hashlib
import json
from security.ecdsa_utils import ECDSAUtils
from security.sha3_utils import SHA3Utils
# from distributed_storage.blockchain_utils import upload_to_blockchain  # 블록체인 저장 함수

# [제조사 용] 업데이트 메시지 생성 & 서명 및 블록체인에 업로드
class UpdateMessageService:
    def __init__(self, ecdsa, sha3):
        """
        - ecdsa: ECDSAUtils 객체 
        - sha3: SHA3Utils 객체 
        """
        self.ecdsa = ecdsa 
        self.sha3 = sha3 

    # 업데이트 메시지 생성
    def create_update_message(self, sw_version, ipfs_url, encrypted_data, encrypted_kbj):
        """업데이트 메시지를 생성하는 함수"""
        # SHA3-256 해시 값 생성
        hEbj = self.sha3.compute_sha3_hash(encrypted_data)  # 암호화된 bj의 해시 값

        # UID 생성: `sw_version` + `ipfs_url`
        uid_combined = f"{sw_version}|{ipfs_url}"

        # 업데이트 메시지(μm) 생성
        update_message = {
            "UID": uid_combined,
            "hEbj": hEbj,
            "encrypted_kbj": encrypted_kbj  # CP-ABE로 암호화된 kbj
        }

        return update_message

    # 업데이트 메시지 서명 및 블록체인 업로드
    def sign_and_upload_update(self, sw_version, ipfs_url, encrypted_data, encrypted_kbj):
        """업데이트 메시지를 서명하고 블록체인에 업로드"""
        # 업데이트 메시지 생성
        update_message = self.create_update_message(sw_version, ipfs_url, encrypted_data, encrypted_kbj)
        print(f"업데이트 메시지 생성 완료: {update_message}")

        # ECDSA 서명 생성
        signature = self.ecdsa.sign_message(update_message)
        print(f"ECDSA 서명 생성 완료: {signature}")

        # 서명 검증
        is_valid = self.ecdsa.verify_signature(update_message, signature)
        if not is_valid:
            print("ECDSA 서명 검증 실패. 블록체인에 업로드 X")
            return None

        # # um과 서명을 블록체인 업로드
        # result = upload_to_blockchain({
        #     "update_message": update_message,
        #     "signature": signature
        # })

        # return result
        