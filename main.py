import asyncio
from blockchain.blockchain_service import BlockChainService
from device.update_manager import UpdateManager
from ipfs.ipfs_service import IPFSClient
from config import BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, IPFS_API_ADDR, MANUFACTURER_PUBLIC_KEY, DEVICE_CPABE_SECRET_KEY

# CP-ABE 초기화 (가정)
from cpabe_init import CPABEInit
from cpabe_crypto import CPABECrypto

cpabe_init = CPABEInit()  # pairing_group='SS512'
cpabe, group, public_key = cpabe_init.get_cpabe_objects()
cpabe_crypto = CPABECrypto(cpabe, group, public_key)

# UpdateManager 관련 import
from device.update_manager import UpdateManager

# def main():
#     # 업데이트 매니저 생성
#     manager = UpdateManager(
#         rpc_url=BLOCKCHAIN_RPC_URL,
#         contract_address=CONTRACT_ADDRESS,
#         abi_path="contract_abi.json",
#         ipfs_addr=IPFS_API_ADDR,
#         ecdsa_public_key=MANUFACTURER_PUBLIC_KEY,  # 실제 파일 경로
#         cpabe_crypto=cpabe_crypto,
#         device_sk=DEVICE_CPABE_SECRET_KEY  # dict
#     )

#     # 테스트용 UID, CID
#     uid = "https://example.com/updates/v1.0"
#     ipfs_cid = "QmExampleCID"

#     # 업데이트 수행
#     try:
#         result_file = manager.perform_update(uid, ipfs_cid, "update.enc")
#         print("최종 복호화된 파일:", result_file)
#     except Exception as e:
#         print("업데이트 실패:", e)

# if __name__ == "__main__":
#     main()
async def main():
    """
    Web3 Listener를 실행하고 블록체인 이벤트를 감지하여 업데이트 수행
    """
    # 블록체인 서비스 및 IPFS 클라이언트 초기화
    blockchain_service = BlockChainService(BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, "contract_abi.json")
    ipfs_client = IPFSClient(IPFS_API_ADDR)

    # UpdateManager 초기화 (블록체인 서비스와 IPFS 클라이언트 연결)
    update_manager = UpdateManager(blockchain_service, ipfs_client, MANUFACTURER_PUBLIC_KEY, None, DEVICE_CPABE_SECRET_KEY)

    print("[Main] 블록체인 이벤트 리스너 시작...")

    # Web3 Listener 실행 (업데이트 이벤트 감지 → 업데이트 수행)
    await blockchain_service.listen_for_updates(update_manager)

if __name__ == "__main__":
    asyncio.run(main())
# =======
# import sys
# import os

# from keygen import keygen;

# # 현재 경로를 기준으로 service 폴더 추가
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

# from encrypt_service import encrypt_and_store
# from decrypt_service import decrypt_and_retrieve
# import update_message_service 

# from crypto.cpabe_init import CPABEInit  # CP-ABE 시스템 가져오기
# from security.ecdsa_utils import ECDSAUtils
# from security.sha3_utils import SHA3Utils

# # 테스트용 사용자 정보
# USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
# POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

# # 파일 경로 설정 (main에서 파라미터로 전달)
# ORIGINAL_FILE_PATH = "data/original_data.bin"
# ENCRYPTED_AES_FILE_PATH = "data/encrypted_data.enc"
# DECRYPTED_AES_FILE_PATH = "data/decrypted_data.bin"

# # 제조사 개인키 & 공개키 pem 파일 경로 설정 (main에서 파라미터로 전달)
# MANUFACTURE_PRIVATE_KEY_PATH = "pem/manufacture_private_key.pem"
# MANUFACTURE_PUBLIC_KEY_PATH = "pem/manufacture_public_key.pem" 

# def main():

#     """ 
#     <main 함수>
#     1. 제조업체에서 개키 PKmi, 개인키 Skmi 생성
#     2. 제조업체에서 암호화 수행 - Es(bj, kbj) & Ec(PKc, kbj, A) (IPFS 업로드 부분은 일단 생략)
#     3. 업데이트 메시지 생성 및 서명 생성 후 블록체인에 업로드 (블록체인에 업로드 하는 과정은 일단 생략)
    
#     4. 디바이스에서 업데이트 메시지 & 서명 검증 (블록체인 관련 부분은 일단 생략)
#     5. hEbj & IPFS에서 다운 받은 Es(bj, kbj) 해시값 비교 (일단 IPFS 생략, 파일 경로를 파라미터로 ㅂ다음)
#     6.. 디바이스에서 복호화 수행 - kbj <- Dc(PKc, kbj, A) , bj <- Ds(bj, kbj)

#     """

#     # 제조사 공개키 PKmi, 개인키 Skmi 생성
#     keygen(MANUFACTURE_PRIVATE_KEY_PATH, MANUFACTURE_PUBLIC_KEY_PATH)

#     # 제조업체에서 암호화 수행 Es(bj, kbj) & Ec(PKc, kbj, A)
#     # SKd는 디바이스에서도 필요하기 때문에 생성 후 전달해놓아야 함
#     print("\nAES & CP-ABE 암호화 수행")
#     encrypted_kbj, device_secret_key = encrypt_and_store(USER_ATTRIBUTES, POLICY, ORIGINAL_FILE_PATH, ENCRYPTED_AES_FILE_PATH)

#     if not encrypted_kbj:
#         print("암호화 실패.")
#         return

#     # 제조사에서 업데이트 메시지 생성 및 서명 생성
#     ecdsa = ECDSAUtils(MANUFACTURE_PUBLIC_KEY_PATH, MANUFACTURE_PRIVATE_KEY_PATH)
#     sha3 = SHA3Utils()
#     update_message, signature = update_message_service.sign_and_upload_update(ecdsa, sha3, "1.0.0", "ipfs_url", ENCRYPTED_AES_FILE_PATH, encrypted_kbj) # 아직 블록체인 업로드 연동 x




#     ## IoT 디바이스에서 서명 검증
#     device_ecdsa = ECDSAUtils(MANUFACTURE_PUBLIC_KEY_PATH)  # 디바이스에서는 서명 검증을 하기 때문에 개인 키 불필요
#     is_valid = device_ecdsa.verify_signature(update_message, signature) # 실제로는 파라미터에 블록체인에서 다운 받은 um, 서명 넣기
#     print(f"IoT 디바이스에서의 서명 검증 여부: ", is_valid)
#     if(is_valid == False):
#         exit()

#     # um 에서 암호화된 데이터 파일의 해시값, 암호화된 kbj 다운
#     hEbj = update_message.get("hEbj", None)
#     encrypted_kbj = update_message.get("encrypted_kbj", None)

#     # 블록체인에서 다운 받은 해시값과 IPFS에서 다운 받은 암호화된 파일의 해시값 비교
#     # 일단 IPFS 제외하고 암호화된 파일의 경로를 파라미터로
#     is_match = sha3.verify_sha3_hash(hEbj, ENCRYPTED_AES_FILE_PATH)
#     print(f"IoT 디바이스에서 hEBJ & IPFS에서 다운 받은 파일 해시 값 비교 여부: ", is_match)
#     if(is_match == False):
#         exit()

#     # 디바이스에서 복호화 수행 
#     # kbj <- Dc(PKc, kbj, A) , bj <- Ds(bj, kbj)
#     # CP-ABE 객체 및 페어링 그룹 가져오기 (복호화에서 필요)
#     cpabe_init = CPABEInit()
#     cpabe, group, public_key = cpabe_init.get_cpabe_objects()

#     print("\nAES & CP-ABE 복호화 수행")
#     result = decrypt_and_retrieve(encrypted_kbj, device_secret_key, ENCRYPTED_AES_FILE_PATH, DECRYPTED_AES_FILE_PATH, cpabe, group, public_key)

#     if result:
#         print("복호화 프로세스 성공")
#     else:
#         print("복호화 실패.")

# if __name__ == "__main__":
#     main()
# >>>>>>> crypto/develop
