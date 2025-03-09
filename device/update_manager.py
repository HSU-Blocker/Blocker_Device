import os
import base64

from blockchain.blockchain_service import BlockChainService
from ipfs.ipfs_service import IPFSClient
from crypto_utils import (
    compute_sha3_hash,
    verify_signature,
    cpabe_decrypt_key,
    aes_decrypt_file
)
from ecdsa_utils import ECDSAUtils
from cpabe_crypto import CPABECrypto

class UpdateManager:
    def __init__(self, rpc_url, contract_address, abi_path, ipfs_addr, ecdsa_public_key, cpabe_crypto, device_sk):
        """
        :param rpc_url: 블록체인 RPC URL
        :param contract_address: SoftwareUpdateManager 컨트랙트 주소
        :param abi_path: ABI 파일 경로
        :param ipfs_addr: IPFS API 주소
        :param ecdsa_public_key: ECDSA 검증용 공개키 (제조사 키)
        :param cpabe_crypto: CPABECrypto 인스턴스 (이미 초기화됨)
        :param device_sk: CP-ABE 디바이스 개인키
        """
        self.bc_service = BlockChainService(rpc_url, contract_address, abi_path)
        self.ipfs_client = IPFSClient(ipfs_addr)
        
        self.ecdsa_utils = ECDSAUtils(
            private_key_path="not_used.pem",  # 안 씀
            public_key_path=ecdsa_public_key,
            generate_new=False
        )
        self.cpabe_crypto = cpabe_crypto
        self.device_sk = device_sk

    def perform_update(self, uid, ipfs_cid, local_enc_file="update.enc"):
        """
        전체 업데이트 프로세스:
        1) 블록체인에서 um 조회 (get_update_metadata)
        2) IPFS에서 파일 다운로드
        3) SHA-3 해시 검증
        4) 서명 검증 (옵션)
        5) CP-ABE 복호화 (AES 키 획득)
        6) (추가) AES 복호화 or 기타 처리
        """
        # 1) 블록체인에서 업데이트 정보 가져오기
        update_info = self.bc_service.get_update_metadata(uid)
        print("[UpdateManager] 블록체인에서 업데이트 정보 수신:", update_info)

        # 2) IPFS에서 암호화된 업데이트 파일 다운로드
        downloaded_file = self.ipfs_client.download_file(ipfs_cid, local_enc_file)
        print("[UpdateManager] IPFS 다운로드 완료:", downloaded_file)

        # 3) SHA-3 해시 검증
        file_hash = compute_sha3_hash(downloaded_file)
        update_hash_hex = update_info["updateHash"].hex()  # bytes32 -> hex str
        if file_hash != update_hash_hex[2:]:  # update_hash_hex는 "0x..." 형태, file_hash는 "abc123..."
            raise Exception(f"해시 불일치! 블록체인 해시={update_hash_hex}, 파일 해시={file_hash}")
        print("[UpdateManager] SHA-3 해시 검증 성공")

        # 4) 서명 검증
        sig = update_info["signature"]
        message_dict = {
            "uid": update_info["uid"],
            "updateHash": update_info["updateHash"].hex(),
            "price": str(update_info["price"]),
            "createdAt": str(update_info["createdAt"])
        }
        if not verify_signature(message_dict, sig, self.ecdsa_utils):
            raise Exception("서명 검증 실패!")
        print("[UpdateManager] ECDSA 서명 검증 성공")

        # 5) CP-ABE 복호화 -> AES 키 (kbj) 획득
        encrypted_key = update_info["encryptedKey"]  # bytes
        # cpabe_decrypt_key(encrypted_key, device_sk, cpabe_crypto)
        kbj = cpabe_decrypt_key(encrypted_key, self.device_sk, self.cpabe_crypto)
        if kbj is None:
            raise Exception("CP-ABE 복호화 실패!")
        print("[UpdateManager] CP-ABE 복호화 성공, AES 키=", kbj)

        # 6) bj 획득
        output_file = "update.bin"
        aes_decrypt_file(downloaded_file, kbj, output_file)
        print("[UpdateManager] AES 복호화 완료 ->", output_file)

        print("[UpdateManager] 업데이트 프로세스 완료!")
        return output_file
