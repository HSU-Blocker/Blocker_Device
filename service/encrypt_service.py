import os
from charm.toolbox.pairinggroup import PairingGroup, GT
from crypto.cpabe_init import CPABEInit
from crypto.cpabe_crypto import CPABECrypto
from crypto.aes_crypto import AESCrypto
from aes_encrypt import aes_encrypt  # AES 암호화 함수
from cpabe_encrypt import cpabe_encrypt  # CP-ABE 암호화 함수

# 파일 경로 설정
ORIGINAL_FILE = "data/original_data.bin"
ENCRYPTED_AES_FILE = "data/encrypted_data.enc"

def encrypt_and_store(user_id, user_attributes, policy):
    """
    AES + CP-ABE 암호화를 한 번에 수행하는 함수
    - user_id: 사용자 ID
    - user_attributes: 사용자 속성 리스트
    - policy: CP-ABE 정책
    """
    # CP-ABE 초기화
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()
    device_secret_key = cpabe_init.generate_secret_key(user_id, user_attributes)

    # GT 그룹에서 난수를 통해 AES 키(kbj) 생성
    kbj = group.random(GT)  # GT 그룹 요소로 키 생성
    print(f"GT 그룹에서 생성된 AES 키(kbj): {kbj}")

    # AES 암호화 실행
    aes_encrypt(group.serialize(kbj)[:32], group, ORIGINAL_FILE, ENCRYPTED_AES_FILE)

    # CP-ABE 암호화 실행
    encrypted_kbj = cpabe_encrypt(kbj, policy, cpabe, group, public_key)
    
    print(f"CP-ABE 암호화된 kbj: {encrypted_kbj}")
    
    return encrypted_kbj  # CP-ABE 암호화된 키 반환

# 암호화 실행 (예제 실행)
if __name__ == "__main__":
    USER_ID = "device_1"
    USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
    POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

    encrypted_kbj = encrypt_and_store(USER_ID, USER_ATTRIBUTES, POLICY)
    print(f"최종 암호화된 kbj: {encrypted_kbj}")
