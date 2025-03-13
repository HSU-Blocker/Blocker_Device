import os
import base64
from security.sha3_utils import SHA3Utils
from service.decrypt_service import decrypt_and_retrieve

# 파일 경로 설정 (main에서 파라미터로 전달)
ORIGINAL_FILE_PATH = "data/original_data.bin"
ENCRYPTED_AES_FILE_PATH = "data/encrypted_data.enc"
DECRYPTED_AES_FILE_PATH = "data/decrypted_data.bin"

class UpdateManager:
    def __init__(self, blockchain_service, ipfs_client, device_ecdsa, cpabe, group, public_key, DEVICE_CPABE_SECRET_KEY):
        """
        :param blockchain_service: 블록체인 서비스 객체
        :param ipfs_client: IPFS 서비스 객체
        :param pkmi: 제조사 공개 키 (ECSA 검증용)
        :param cpabe_crypto: CPABECrypto 인스턴스 (초기화됨)
        :param skd: 디바이스의 CP-ABE 개인 키
        """
        self.blockchain_service = blockchain_service
        self.ipfs_client = ipfs_client
        self.device_ecdsa = device_ecdsa
        self.cpabe = cpabe
        self.group = group
        self.pkc = public_key
        self.skd = DEVICE_CPABE_SECRET_KEY

    async def perform_update(self, uid):
        """
        업데이트 실행 (블록체인에서 정보 조회 → IPFS 다운로드 → 검증)
        """
        """
        전체 업데이트 프로세스:
        1) 블록체인에서 um 조회 (get_update_metadata)
        2) UID에서 CID 추출 후, IPFS에서 파일 다운로드
        3) 서명 검증SHA-3 해시 검증
        4) SHA-3 해시 검증
        5) CP-ABE 복호화 + AES 복호화
        """
        print(f"[UpdateManager] 업데이트 수행 시작: UID={uid}")

        # 1) 블록체인에서 업데이트 정보 가져오기
        blockchain_data = self.blockchain_service.get_update_metadata(uid)
        print("[UpdateManager] 블록체인에서 업데이트 정보 수신:", blockchain_data)
        
        # 2-1) UID에서 CID 추출
        ipfs_cid, version = self.extract_cid_from_uid(blockchain_data["uid"])
        print(f"[UpdateManager] IPFS CID 추출 완료: {ipfs_cid} (Version: {version})")

        # 2-2) IPFS에서 암호화된 업데이트 파일 ENCRYPTED_AES_FILE_PATH에 다운로드
        ipfs_downloaded_file = self.ipfs_client.download_file(ipfs_cid, ENCRYPTED_AES_FILE_PATH)
        print("[UpdateManager] IPFS 다운로드 완료:", ipfs_downloaded_file)
        
        ## 암호화 병합
        # 3) 서명 검증
        signature = blockchain_data["signature"]
        update_message = {
            "uid": blockchain_data["uid"],
            "hEbj": blockchain_data["updateHash"].hex(),
            "encrypted_kbj": str(blockchain_data["encryptedKey"]), # Ec(PKc, kbj, A)
        }
        is_valid = self.device_ecdsa.verify_signature(update_message, signature) # 실제로는 파라미터에 블록체인에서 다운 받은 um, 서명 넣기
        print(f"[UpdateManager] IoT 디바이스에서의 서명 검증 여부: ", is_valid)
        if(is_valid == False):
            exit()
            
        # 4) SHA-3 해시 검증
        hEbj = blockchain_data["updateHash"]
        is_match = SHA3Utils.verify_sha3_hash(hEbj, ENCRYPTED_AES_FILE_PATH)
        print(f"[UpdateManager] IoT 디바이스에서 hEBJ & IPFS에서 다운 받은 파일 해시 값 비교 여부: ", is_match)
        if(is_match == False):
            exit()

        # 5) CP-ABE 복호화 + AES 복호화 -> AES 키 (kbj) 획득 + Ds(bj,kbj)
        encrypted_kbj = blockchain_data["encryptedKey"]  # bytes
        result = decrypt_and_retrieve(encrypted_kbj, self.skd, ENCRYPTED_AES_FILE_PATH, DECRYPTED_AES_FILE_PATH, self.cpabe, self.group, self.pkc)
        if result:
            print("복호화 프로세스 성공")
        else:
            print("복호화 실패.")
        ##
    
    def extract_cid_from_uid(self, uid):
        if "∥" not in uid:
            raise ValueError(f"UID 형식이 올바르지 않습니다: {uid}")

        cid, version = uid.split("∥", 1)  # '∥' 기준으로 URL과 버전 분리
    
        return cid, version