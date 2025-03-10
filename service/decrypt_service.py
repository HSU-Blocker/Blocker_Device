import os
import sys
from charm.toolbox.pairinggroup import GT

# 현재 경로를 기준으로 crypto 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto.cpabe_init import CPABEInit
from crypto.aes_decrypt import AESDecrypt
from crypto.cpabe_decrypt import CPABEDecrypt

def decrypt_kbj_with_cpabe(encrypted_kbj, user_id, user_attributes):
    """CP-ABE를 이용하여 AES 키(kbj)를 복호화하는 함수"""
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()
    device_secret_key = cpabe_init.generate_secret_key(user_id, user_attributes)

    cpabe_decryptor = CPABEDecrypt(cpabe, group, public_key)
    decrypted_kbj = cpabe_decryptor.decrypt(device_secret_key, encrypted_kbj)

    if decrypted_kbj is None:
        print("CP-ABE 복호화 실패: 접근 정책 불충족 또는 복호화 오류")
        return None

    decrypted_kbj_aes_key = group.serialize(decrypted_kbj)[:32]
    print(f"최종 복호화된 AES kbj key: {decrypted_kbj_aes_key}")

    return decrypted_kbj_aes_key

def decrypt_bj_with_aes(aes_key, encrypted_aes_file, decrypted_aes_file):
    """AES 복호화를 수행하고 결과를 저장하는 함수"""
    aes_decryptor = AESDecrypt(aes_key)
    encrypted_bj = AESDecrypt.load_from_file(encrypted_aes_file)

    try:
        decrypted_bj = aes_decryptor.decrypt(encrypted_bj)
        print(f"bj 복호화 완료, 데이터 크기: {len(decrypted_bj)} bytes")

        with open(decrypted_aes_file, "wb") as f:
            f.write(decrypted_bj)
        print(f"복호화된 데이터 저장 완료: {decrypted_aes_file}")

        return True
    except ValueError as e:
        print(f"AES 복호화 실패: {e}")
        return False

def decrypt_and_retrieve(encrypted_kbj, user_id, user_attributes, encrypted_aes_file, decrypted_aes_file):
    """CP-ABE 및 AES 복호화를 한 번에 수행하는 함수"""
    aes_key = decrypt_kbj_with_cpabe(encrypted_kbj, user_id, user_attributes)

    if aes_key is None:
        print("복호화 프로세스 중단: AES 키 복호화 실패")
        return False

    return decrypt_bj_with_aes(aes_key, encrypted_aes_file, decrypted_aes_file)
    