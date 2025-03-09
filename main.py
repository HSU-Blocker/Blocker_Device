import os
from cpabe.cpabe_init import CPABEInit
from cpabe.cpabe_crypto import CPABECrypto
from aes.aes_init import AESInit
from aes.aes_crypto import AESCrypto

# 원본 데이터 파일 경로
original_file = "data/original_data.bin"
encrypted_aes_file = "data/encrypted_data.enc"
decrypted_aes_file = "data/decrypted_data.bin"

# CP-ABE 시스템 초기화
cpabe_init = CPABEInit()
cpabe, group, public_key = cpabe_init.get_cpabe_objects()

# 사용자 속성 및 개인키 생성
user_id = "device_1"
user_attributes = ["ATTR1", "ATTR2", "ATTR4"]
device_secret_key = cpabe_init.generate_secret_key(user_id, user_attributes)

# CP-ABE 암호화 시스템 초기화
cpabe_crypto = CPABECrypto(cpabe, group, public_key)

# AES 키(kbj) 생성
aes_init = AESInit()
kbj = aes_init.create_aes_key()

# AES 암호화 시스템 초기화
aes_crypto = AESCrypto()

# 원본 데이터(bj) 불러오기
with open(original_file, "rb") as f:
    bj = f.read()
print(f"원본 데이터 크기: {len(bj)} bytes")

# AES256을 이용하여 kbj로 데이터(bj) 암호화
# Es(bj, kbj)
encrypted_bj = aes_crypto.encrypt(bj, kbj)

# 암호화된 데이터(bj)를 파일에 저장 (나중엔 IPFS로 업로드 로직 추가)
with open(encrypted_aes_file, "wb") as f:
    f.write(encrypted_bj)
print(f"bj 암호화 완료: {encrypted_aes_file}")

# CP-ABE를 이용한 대칭키(kbj) 암호화
# Ec(PKc, kbj, A)
policy = "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))"
encrypted_kbj = cpabe_crypto.encrypt(kbj, policy)
print("CP-ABE 암호화된 kbj 생성 완료")

# CP-ABE 암호화된 AES 키 복호화
decrypted_kbj = cpabe_crypto.decrypt(device_secret_key, encrypted_kbj)

if decrypted_kbj is None:
    print("CP-ABE 복호화 실패: 접근 정책 불충족")
    exit(1)

# AES 암호화된 데이터(bj) 불러오기
with open(encrypted_aes_file, "rb") as f:
    loaded_encrypted_bj = f.read()

# AES 복호화
decrypted_bj = aes_crypto.decrypt(loaded_encrypted_bj, decrypted_kbj)
print(f"bj 복호화 완료, 데이터 크기: {len(decrypted_bj)} bytes")

# 복호화된 데이터(bj)를 파일에 저장
with open(decrypted_aes_file, "wb") as f:
    f.write(decrypted_bj)
print(f"복호화된 데이터 bj 저장 완료: {decrypted_aes_file}")
