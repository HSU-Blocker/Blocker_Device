import os
import sys
from charm.toolbox.pairinggroup import GT

# 현재 경로를 기준으로 crypto 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto.cpabe_init import CPABEInit
from crypto.aes_encrypt import AESEncrypt
from crypto.cpabe_encrypt import CPABEEncrypt

# 파일 경로 설정
ORIGINAL_FILE = "../data/original_data.bin"
ENCRYPTED_AES_FILE = "../data/encrypted_data.enc"

def encrypt_bj_with_aes(kbj, group):
    """
    AES 암호화를 수행하고 결과를 저장하는 함수
    - kbj: GT 그룹에서 생성된 AES 대칭키
    - group: 페어링 그룹 객체 (CP-ABE와 공유)
    """
    # AES 키 변환 (GT 요소 → 32바이트 키 변환)
    kbj_bytes = group.serialize(kbj)
    aes_key = kbj_bytes[:32]  # AES 256-bit (32바이트) 키 생성

    # AES 암호화 실행
    aes = AESEncrypt(aes_key)
    with open(ORIGINAL_FILE, "rb") as f:
        bj_data = f.read()
    encrypted_bj = aes.encrypt(bj_data)

    # AES 암호화된 데이터 저장
    AESEncrypt.save_to_file(encrypted_bj, ENCRYPTED_AES_FILE)

    print(f"AES 암호화 완료, 저장 위치: {ENCRYPTED_AES_FILE}")
    return aes_key  # AES 키 반환

def encrypt_kbj_with_cpabe(kbj, policy, cpabe, group, public_key):
    """
    CP-ABE를 이용하여 AES 키(kbj)를 암호화하는 함수
    - kbj: GT 그룹에서 생성된 AES 대칭키
    - policy: CP-ABE 접근 정책
    - cpabe: CP-ABE 객체
    - group: 페어링 그룹 객체
    - public_key: CP-ABE 공개키
    """
    cpabe_encryptor = CPABEEncrypt(cpabe, group, public_key)
    encrypted_kbj = cpabe_encryptor.encrypt(kbj, policy)

    print(f"CP-ABE 암호화된 kbj: {encrypted_kbj}")
    return encrypted_kbj  # CP-ABE 암호화된 AES 키 반환

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
    aes_key = encrypt_bj_with_aes(kbj, group)

    # CP-ABE 암호화 실행
    encrypted_kbj = encrypt_kbj_with_cpabe(kbj, policy, cpabe, group, public_key)

    return encrypted_kbj  # CP-ABE 암호화된 AES 키 반환

# 암호화 실행 (예제 실행)
if __name__ == "__main__":
    USER_ID = "device_1"
    USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
    POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

    encrypted_kbj = encrypt_and_store(USER_ID, USER_ATTRIBUTES, POLICY)
    print(f"bj & kbj 암호화 완료.")
