import os
from crypto.cpabe_init import CPABEInit
from security.ecdsa_utils import ECDSAUtils
from security.sha3_utils import SHA3Utils
from service.decrypt_service import decrypt_and_retrieve

# (테스트용) 블록체인에서 받은 데이터
BLOCKCHAIN_UM = {
    "uid": "https://ipfs.io/ipfs/QmEncryptedFile∥1.0.0",
    "updateHash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",  # SHA-3 해시
    "encryptedKey": b"\x01\x02\x03\x04EncryptedKBJData",  # 실제 사용시 블록체인에서 받아야 함
    "signature": b"\x05\x06\x07\x08SignatureData",  # ECDSA 서명 (검증용)
}

# (테스트용) IPFS에서 받은 암호화된 파일
ENCRYPTED_AES_FILE_PATH = "data/encrypted_data.enc"
DECRYPTED_AES_FILE_PATH = "data/decrypted_data.bin"

def test_device_decryption():
    print("[crypto_test] 디바이스 복호화 테스트 시작")

    # CP-ABE 키 초기화
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()

    # SKd 생성
    ATTRIBUTES = ["ATTR1", "ATTR2", "ATTR4"]
    device_skd = cpabe_init.generate_device_secret_key(ATTRIBUTES)

    # ECDSA 서명 검증
    device_ecdsa = ECDSAUtils("pem/manufacture_public_key.pem")  # 제조업체 공개키 로드
    update_message = {
        "uid": BLOCKCHAIN_UM["uid"],
        "hEbj": BLOCKCHAIN_UM["updateHash"],
        "encrypted_kbj": str(BLOCKCHAIN_UM["encryptedKey"]),
    }

    is_valid_signature = device_ecdsa.verify_signature(update_message, BLOCKCHAIN_UM["signature"])
    print(f"서명 검증 결과: {is_valid_signature}")
    if not is_valid_signature:
        print("서명 검증 실패! 프로세스 중단")
        return

    # SHA-3 해시 검증
    is_valid_hash = SHA3Utils.verify_sha3_hash(BLOCKCHAIN_UM["updateHash"], ENCRYPTED_AES_FILE_PATH)
    print(f"해시 검증 결과: {is_valid_hash}")
    if not is_valid_hash:
        print("해시 검증 실패! 프로세스 중단")
        return

    # CP-ABE 복호화 + AES 복호화
    encrypted_kbj = BLOCKCHAIN_UM["encryptedKey"]
    decryption_success = decrypt_and_retrieve(encrypted_kbj, device_skd, ENCRYPTED_AES_FILE_PATH, DECRYPTED_AES_FILE_PATH, cpabe, group, public_key)

    if decryption_success:
        print("복호화 성공!")
        if os.path.exists(DECRYPTED_AES_FILE_PATH):
            print(f"복호화된 파일이 생성됨: {DECRYPTED_AES_FILE_PATH}")
        else:
            print("복호화된 파일이 생성되지 않음!")
    else:
        print("복호화 실패!")

if __name__ == "__main__":
    test_device_decryption()
