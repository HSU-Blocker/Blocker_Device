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

# 파일 경로 설정 (main에서 파라미터로 전달)
ORIGINAL_FILE = "data/original_data.bin"
ENCRYPTED_AES_FILE = "data/encrypted_data.enc"
DECRYPTED_AES_FILE = "data/decrypted_data.bin"

def main():
    """
    1. AES + CP-ABE 암호화를 수행하고
    2. 생성된 `encrypted_kbj`를 이용해 복호화를 수행하는 메인 함수
    """
    print("\nAES & CP-ABE 암호화 수행")
    encrypted_kbj = encrypt_and_store(USER_ID, USER_ATTRIBUTES, POLICY, ORIGINAL_FILE, ENCRYPTED_AES_FILE)

    if not encrypted_kbj:
        print("암호화 실패.")
        return

    print("\nAES & CP-ABE 복호화 수행")
    result = decrypt_and_retrieve(encrypted_kbj, USER_ID, USER_ATTRIBUTES, ENCRYPTED_AES_FILE, DECRYPTED_AES_FILE)

    if result:
        print("복호화 프로세스 성공")
    else:
        print("복호화 실패.")

if __name__ == "__main__":
    main()