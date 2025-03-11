import sys
import os

from keygen import keygen;

# 현재 경로를 기준으로 service 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

# from encrypt_service import encrypt_and_store
# from decrypt_service import decrypt_and_retrieve
# from crypto.cpabe_init import CPABEInit  # CP-ABE 시스템 가져오기
from update_message_service import UpdateMessage
from security.ecdsa_utils import ECDSAUtils
from security.sha3_utils import SHA3Utils

# 테스트용 사용자 정보
USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

# 파일 경로 설정 (main에서 파라미터로 전달)
ORIGINAL_FILE = "data/original_data.bin"
ENCRYPTED_AES_FILE = "data/encrypted_data.enc"
DECRYPTED_AES_FILE = "data/decrypted_data.bin"

# 제조사 개인키 & 공개키 pem 파일 경로 설정 (main에서 파라미터로 전달)
manufacture_private_key = "pem/manufacture_private_key.pem"
manufacture_public_key = "pem/manufacture_public_key.pem" 

def main():

    # 제조사 공개키 PKmi, 개인키 Skmi 생성
    keygen(manufacture_private_key, manufacture_public_key)

    """
    1. AES + CP-ABE 암호화를 수행하고
    2. 생성된 `encrypted_kbj`를 이용해 복호화를 수행하는 메인 함수
    """
    # 암호화 (제조업체)
    # SKd는 디바이스에서도 필요하기 때문에 전달해놓아야 함
    print("\nAES & CP-ABE 암호화 수행")
    encrypted_kbj, device_secret_key = encrypt_and_store(USER_ATTRIBUTES, POLICY, ORIGINAL_FILE, ENCRYPTED_AES_FILE)

    if not encrypted_kbj:
        print("암호화 실패.")
        return

    # 제조사에서 업데이트 메시지 생성 및 서명 생성
    ecdsa = ECDSAUtils(manufacture_private_key, manufacture_public_key)
    sha3 = SHA3Utils()
    update_message_service.sign_and_upload_update(ecdsa, sha3, "1.0.0", "ipfs_url", ENCRYPTED_AES_FILE, encrypted_kbj) # 아직 블록체인 업로드 연동 x

    # 복호화 (디바이스)
    # CP-ABE 객체 및 페어링 그룹 가져오기 (복호화에서 필요)
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()

    print("\nAES & CP-ABE 복호화 수행")
    result = decrypt_and_retrieve(encrypted_kbj, device_secret_key, ENCRYPTED_AES_FILE, DECRYPTED_AES_FILE, cpabe, group, public_key)

    if result:
        print("복호화 프로세스 성공")
    else:
        print("복호화 실패.")

if __name__ == "__main__":
    main()
