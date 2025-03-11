import sys
import os

from keygen import keygen;

# 현재 경로를 기준으로 service 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

from encrypt_service import encrypt_and_store
from decrypt_service import decrypt_and_retrieve
import update_message_service 

from crypto.cpabe_init import CPABEInit  # CP-ABE 시스템 가져오기
from security.ecdsa_utils import ECDSAUtils
from security.sha3_utils import SHA3Utils

# 테스트용 사용자 정보
USER_ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
POLICY = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"

# 파일 경로 설정 (main에서 파라미터로 전달)
ORIGINAL_FILE_PATH = "data/original_data.bin"
ENCRYPTED_AES_FILE_PATH = "data/encrypted_data.enc"
DECRYPTED_AES_FILE_PATH = "data/decrypted_data.bin"

# 제조사 개인키 & 공개키 pem 파일 경로 설정 (main에서 파라미터로 전달)
MANUFACTURE_PRIVATE_KEY_PATH = "pem/manufacture_private_key.pem"
MANUFACTURE_PUBLIC_KEY_PATH = "pem/manufacture_public_key.pem" 

def main():

    """ 
    <main 함수>
    1. 제조업체에서 개키 PKmi, 개인키 Skmi 생성
    2. 제조업체에서 암호화 수행 - Es(bj, kbj) & Ec(PKc, kbj, A) (IPFS 업로드 부분은 일단 생략)
    3. 업데이트 메시지 생성 및 서명 생성 후 블록체인에 업로드 (블록체인에 업로드 하는 과정은 일단 생략)
    
    4. 디바이스에서 업데이트 메시지 & 서명 검증 (블록체인 관련 부분은 일단 생략)
    5. hEbj & IPFS에서 다운 받은 Es(bj, kbj) 해시값 비교 (일단 IPFS 생략, 파일 경로를 파라미터로 ㅂ다음)
    6.. 디바이스에서 복호화 수행 - kbj <- Dc(PKc, kbj, A) , bj <- Ds(bj, kbj)

    """

    # 제조사 공개키 PKmi, 개인키 Skmi 생성
    keygen(MANUFACTURE_PRIVATE_KEY_PATH, MANUFACTURE_PUBLIC_KEY_PATH)

    # 제조업체에서 암호화 수행 Es(bj, kbj) & Ec(PKc, kbj, A)
    # SKd는 디바이스에서도 필요하기 때문에 생성 후 전달해놓아야 함
    print("\nAES & CP-ABE 암호화 수행")
    encrypted_kbj, device_secret_key = encrypt_and_store(USER_ATTRIBUTES, POLICY, ORIGINAL_FILE_PATH, ENCRYPTED_AES_FILE_PATH)

    if not encrypted_kbj:
        print("암호화 실패.")
        return

    # 제조사에서 업데이트 메시지 생성 및 서명 생성
    ecdsa = ECDSAUtils(MANUFACTURE_PUBLIC_KEY_PATH, MANUFACTURE_PRIVATE_KEY_PATH)
    sha3 = SHA3Utils()
    update_message, signature = update_message_service.sign_and_upload_update(ecdsa, sha3, "1.0.0", "ipfs_url", ENCRYPTED_AES_FILE_PATH, encrypted_kbj) # 아직 블록체인 업로드 연동 x




    ## IoT 디바이스에서 서명 검증
    device_ecdsa = ECDSAUtils(MANUFACTURE_PUBLIC_KEY_PATH)  # 디바이스에서는 서명 검증을 하기 때문에 개인 키 불필요
    is_valid = device_ecdsa.verify_signature(update_message, signature) # 실제로는 파라미터에 블록체인에서 다운 받은 um, 서명 넣기
    print(f"IoT 디바이스에서의 서명 검증 여부: ", is_valid)
    if(is_valid == False)
        exit()

    # um 에서 암호화된 데이터 파일의 해시값, 암호화된 kbj 다운
    hEbj = update_message.get("hEbj", None)
    encrypted_kbj = update_message.get("encrypted_kbj", None)

    # 블록체인에서 다운 받은 해시값과 IPFS에서 다운 받은 암호화된 파일의 해시값 비교
    # 일단 IPFS 제외하고 암호화된 파일의 경로를 파라미터로
    is_match = sha3.verify_sha3_hash(hEbj, ENCRYPTED_AES_FILE_PATH)
    print(f"IoT 디바이스에서 hEBJ & IPFS에서 다운 받은 파일 해시 값 비겨 여부: ", is_match)
    if(is_match == False)
        exit()

    # 디바이스에서 복호화 수행 
    # kbj <- Dc(PKc, kbj, A) , bj <- Ds(bj, kbj)
    # CP-ABE 객체 및 페어링 그룹 가져오기 (복호화에서 필요)
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()

    print("\nAES & CP-ABE 복호화 수행")
    result = decrypt_and_retrieve(encrypted_kbj, device_secret_key, ENCRYPTED_AES_FILE_PATH, DECRYPTED_AES_FILE_PATH, cpabe, group, public_key)

    if result:
        print("복호화 프로세스 성공")
    else:
        print("복호화 실패.")

if __name__ == "__main__":
    main()
