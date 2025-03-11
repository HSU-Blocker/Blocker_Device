import os
import sys
from charm.toolbox.pairinggroup import GT

# 현재 경로를 기준으로 crypto 폴더 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto.cpabe_init import CPABEInit
from crypto.aes_encrypt import AESEncrypt
from crypto.cpabe_encrypt import CPABEEncrypt

# Es(bj, kbj)
def encrypt_bj_with_aes(kbj, group, original_file, encrypted_aes_file):
    """
    AES 암호화를 수행하고 결과를 저장하는 함수
    - kbj: GT 그룹에서 생성된 AES 대칭키
    - group: 페어링 그룹 객체 (CP-ABE와 공유)
    - original_file: 원본 데이터 파일 경로
    - encrypted_aes_file: 암호화된 데이터 저장 경로
    """
    kbj_bytes = group.serialize(kbj)
    aes_key = kbj_bytes[:32]  # AES 256-bit (32바이트) 키 생성

    aes = AESEncrypt(aes_key)
    with open(original_file, "rb") as f:
        bj_data = f.read()
    encrypted_bj = aes.encrypt(bj_data)

    AESEncrypt.save_to_file(encrypted_bj, encrypted_aes_file)

    print(f"AES 암호화 완료, 저장 위치: {encrypted_aes_file}")
    return aes_key

# Ec(PKc, kbj, SKd)
def encrypt_kbj_with_cpabe(kbj, policy, cpabe, group, public_key):
    """CP-ABE를 이용하여 AES 키(kbj)를 암호화하는 함수"""
    cpabe_encryptor = CPABEEncrypt(cpabe, group, public_key)
    encrypted_kbj = cpabe_encryptor.encrypt(kbj, policy)

    print(f"CP-ABE 암호화된 kbj: {encrypted_kbj}")
    return encrypted_kbj

# bj & kbj 암호화 및 암호화된 bj를 파일로 저장
# 실제로는 암호화된 bj 파일을 IPFS에 업로드 & 암호화된 kbj는 um에 포함하여 블록체인 업로드 필요
def encrypt_and_store(user_attributes, policy, original_file, encrypted_aes_file):
    """
    AES + CP-ABE 암호화를 수행하는 함수
    - user_attributes: 사용자 속성 리스트
    - policy: CP-ABE 정책
    - original_file: 원본 데이터 파일 경로
    - encrypted_aes_file: 암호화된 데이터 저장 경로
    """
    cpabe_init = CPABEInit()
    cpabe, group, public_key = cpabe_init.get_cpabe_objects()

    # 기존: device_secret_key를 내부에서만 사용 → 변경: 반환하도록 수정
    device_secret_key = cpabe_init.generate_device_secret_key(user_attributes)

    kbj = group.random(GT)  # GT 그룹 요소로 키 생성
    print(f"GT 그룹에서 생성된 AES 키(kbj): {kbj}")

    aes_key = encrypt_bj_with_aes(kbj, group, original_file, encrypted_aes_file)
    encrypted_kbj = encrypt_kbj_with_cpabe(kbj, policy, cpabe, group, public_key)

    # `device_secret_key`를 함께 반환하여 복호화 시 동일한 키 사용 가능
    return encrypted_kbj, device_secret_key
