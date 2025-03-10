import os
import sys
from charm.toolbox.pairinggroup import GT

# 현재 경로를 기준으로 crypto 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto.cpabe_init import CPABEInit
from crypto.aes_decrypt import AESDecrypt
from crypto.cpabe_decrypt import CPABEDecrypt

# 파일 경로 설정
ENCRYPTED_AES_FILE = "../data/encrypted_data.enc"
DECRYPTED_AES_FILE = "../data/decrypted_data.bin"

def decrypt_kbj_with_cpabe(encrypted_kbj, user_id, user_attributes):
    """
    CP-ABE를 이용하여 AES 키(kbj)를 복호화하는 함수
    - encrypted_kbj: 암호화된 AES 키
    - user_id: 사용자 ID
    - user_attributes: 사용자 속성 리스트
    """
    # CP-ABE 초기화
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()

    # 사용자 개인 키 생성 (또는 불러오기)
    device_secret_key = cpabe_init.generate_secret_key(user_id, user_attributes)

    # CP-ABE 복호화 수행
    cpabe_decryptor = CPABEDecrypt(cpabe, group, public_key)
    decrypted_kbj = cpabe_decryptor.decrypt(device_secret_key, encrypted_kbj)

    if decrypted_kbj is None:
        print("P-ABE 복호화 실패: 접근 정책 불충족 또는 복호화 오류")
        return None

    # GT 요소를 AES 키(32바이트)로 변환
    decrypted_kbj_aes_key = group.serialize(decrypted_kbj)[:32]
    print(f"최종 복호화 된 AES kbj key: {decrypted_kbj_aes_key}")

    return decrypted_kbj_aes_key  # AES에서 사용할 키 반환

def decrypt_bj_with_aes(aes_key):
    """
    AES 복호화를 수행하고 결과를 저장하는 함수
    - aes_key: AES 복호화 키 (32바이트)
    """
    # AES 복호화 객체 생성
    aes_decryptor = AESDecrypt(aes_key)

    # AES 암호화된 데이터 불러오기
    encrypted_bj = AESDecrypt.load_from_file(ENCRYPTED_AES_FILE)

    # AES 복호화 수행
    try:
        decrypted_bj = aes_decryptor.decrypt(encrypted_bj)
        print(f"bj 복호화 완료, 데이터 크기: {len(decrypted_bj)} bytes")

        # 복호화된 데이터 저장
        with open(DECRYPTED_AES_FILE, "wb") as f:
            f.write(decrypted_bj)
        print(f"복호화된 데이터 bj 저장 완료: {DECRYPTED_AES_FILE}")

        return True
    except ValueError as e:
        print(f"AES 복호화 실패: {e}")
        return False

def decrypt_and_retrieve(encrypted_kbj, user_id, user_attributes):
    """
    CP-ABE 및 AES 복호화를 한 번에 수행하는 함수
    - encrypted_kbj: CP-ABE로 암호화된 AES 키
    - user_id: 사용자 ID
    - user_attributes: 사용자 속성 리스트
    """
    # CP-ABE 복호화를 통해 AES 키 복호화
    aes_key = decrypt_kbj_with_cpabe(encrypted_kbj, user_id, user_attributes)

    if aes_key is None:
        print("복호화 프로세스 중단: AES 키 복호화 실패")
        return False

    # AES 복호화 수행
    return decrypt_bj_with_aes(aes_key)

# 복호화 실행 (예제 실행)
if __name__ == "__main__":
    USER_ID = "device_1"
    USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]

    # 예제: 암호화된 AES 키 (CP-ABE로 암호화된 `kbj`)
    encrypted_kbj = {
        "C_tilde": b"...",  # 예제 데이터 (실제 블록체인에서 가져와야 함)
        "C": b"...",
        "Cy": { "ATTR1": [1234, 5678], "ATTR2": [91011, 1213] },
        "Cyp": { "ATTR1": [4321, 8765], "ATTR2": [11109, 1312] },
        "policy": "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"
    }

    # 복호화 실행
    result = decrypt_and_retrieve(encrypted_kbj, USER_ID, USER_ATTRIBUTES)

    if result:
        print("전체 복호화 프로세스 성공!")
    else:
        print("복호화 프로세스 실패!")
