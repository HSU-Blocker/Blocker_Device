# import os
# from crypto.cpabe_init import CPABEInit
# from crypto.cpabe_crypto import CPABECrypto
# from crypto.aes_crypto import AESCrypto
# from charm.toolbox.pairinggroup import GT

# from update_message_utils import UpdateMessage
# from security.ecdsa_utils import ECDSAUtils
# from security.sha3_utils import SHA3Utils

# # 원본 데이터 파일 경로
# original_file = "data/original_data.bin"
# encrypted_aes_file = "data/encrypted_data.enc"
# decrypted_aes_file = "data/decrypted_data.bin"

# # CP-ABE 시스템 초기화
# cpabe_init = CPABEInit()
# cpabe, group, public_key = cpabe_init.get_cpabe_objects()

# # 사용자 속성 및 개인키 생성
# user_id = "device_1"
# user_attributes = ["ATTR1", "ATTR2", "ATTR4"]
# device_secret_key = cpabe_init.generate_secret_key(user_id, user_attributes)

# ## --- 암호화 ---
# # CP-ABE 암호화 시스템 초기화
# cpabe_crypto = CPABECrypto(cpabe, group, public_key)

# # GT 그룹에서 난수를 통해 kbj 생성
# kbj = group.random(GT)  # GT 그룹 요소로 키 생성
# print(f"GT 그룹에서 생성된 AES 키(kbj): {kbj}")

# # AES 암호화 시스템 초기화
# aes_crypto = AESCrypto(group.serialize(kbj)[:32])  # GT 요소 직렬화 후 AES에서 사용 가능한 kbj로 변환

# # 원본 데이터(bj) 불러오기
# with open(original_file, "rb") as f:
#     bj = f.read()
# print(f"원본 데이터 크기: {len(bj)} bytes")

# # AES256을 이용하여 GT 그룹의 kbj로 데이터(bj) 암호화
# # Es(bj, kbj)
# encrypted_bj = aes_crypto.encrypt(bj)

# # 암호화된 데이터(bj)를 파일에 저장
# # 해당 파일을 IPFS에 업로드 필요
# with open(encrypted_aes_file, "wb") as f:
#     f.write(encrypted_bj)
# print(f"bj 암호화 완료: {encrypted_aes_file}")

# # CP-ABE를 이용한 대칭키(kbj) 암호화
# # Ec(PKc, kbj, A)
# # 암호화한 kbj인 encrypted_kbj 를 um에 포함하여 블록체인에 업로드 필요
# policy = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"
# encrypted_kbj = cpabe_crypto.encrypt(kbj, policy)
# print(f"CP-ABE 암호화된 kbj 생성 완료, 암호화된 kbj: {encrypted_kbj}")

# # ## 업데이트 메시지 생성, 서명 및 블록체인 업로드
# # update_message_utils = UpdateMessage()
# # update_message_utils.sign_and_upload_update("1.0.0", "ipfs_url", encrypted_aes_file, encrypted_kbj)

# # ## IPFS에 encrypted_aes_file 업로드

# ## --- 복호화 ---
# # 블록체인에서 um, 서명 다운로드
# # IPFS에서 암호화된 encrypted_aes_file 다운로드

# # # 서명 검증
# # ecdsa = ECDSAUtils()
# # ecdsa.verify_signature(update_message, signature)

# # # 해시 값 검증
# # hash_result = SHA3Utils.verify_sha3_hash(hEbj, encrypted_aes_file_by_ipfs)

# # CP-ABE 암호화된 kbj 복호화
# # kbj <- Dc(PKc, kbj, SKd)
# decrypted_kbj = cpabe_crypto.decrypt(device_secret_key, encrypted_kbj)

# # 복호화된 kbj를 AES에서 사용 가능한 kbj로 변환
# decrypted_kbj_aes_key = group.serialize(decrypted_kbj)[:32]
# print(f"최종 복호화 된 AES kbj key: {decrypted_kbj_aes_key}")

# # AES 키 길이 체크
# if len(decrypted_kbj_aes_key) != 32:
#     print("AES 키 길이가 32바이트가 아닙니다! 변환 오류 발생.")
#     exit(1)

# # AES 복호화 객체 불러오기
# aes_crypto_decrypt = AESCrypto(decrypted_kbj_aes_key)

# # AES 암호화된 데이터(bj) 불러오기
# with open(encrypted_aes_file, "rb") as f:
#     loaded_encrypted_bj = f.read()

# # AES 복호화 수행
# try:
#     decrypted_bj = aes_crypto_decrypt.decrypt(loaded_encrypted_bj)
#     print(f"bj 복호화 완료, 데이터 크기: {len(decrypted_bj)} bytes")

#     # 복호화된 데이터(bj)를 파일에 저장
#     with open(decrypted_aes_file, "wb") as f:
#         f.write(decrypted_bj)
#     print(f"복호화된 데이터 bj 저장 완료: {decrypted_aes_file}")

# except ValueError as e:
#     print(f"AES 복호화 실패: {e}")
#     exit(1)

import sys
import os

# 현재 경로를 기준으로 service 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

from encrypt_service import encrypt_and_store
from decrypt_service import decrypt_and_retrieve

# 테스트용 사용자 정보
USER_ID = "device_1"
USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

def main():
    """
    1. AES + CP-ABE 암호화를 수행하고
    2. 생성된 `encrypted_kbj`를 이용해 복호화를 수행하는 메인 함수
    """
    print("\nAES & CP-ABE 암호화 수행")
    encrypted_kbj = encrypt_and_store(USER_ID, USER_ATTRIBUTES, POLICY)

    if not encrypted_kbj:
        print("암호화 실패")
        return

    print("\nAES & CP-ABE 복호화 수행")
    result = decrypt_and_retrieve(encrypted_kbj, USER_ID, USER_ATTRIBUTES)

    if result:
        print("전체 암호화 & 복호화 프로세스 성공")
    else:
        print("복호화 실패!")

if __name__ == "__main__":
    main()
