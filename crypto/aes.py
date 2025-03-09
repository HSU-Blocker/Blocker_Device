import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

# 256비트 AES 대칭키 kbj 생성
def create_aes_key():
    aes_key = get_random_bytes(32)  # 256비트 AES 키 (32바이트)
    print(f"AES Key (256-bit): {aes_key.hex()}")
    return aes_key

# AES256 암호화 Es(bj, kbj)
def encrypt_with_aes(data: bytes, key: bytes) -> bytes:
    if not isinstance(data, bytes):
        raise ValueError("암호화할 데이터는 바이트 형식이어야 합니다.")

    iv = get_random_bytes(16)  # AES 블록 크기 (16바이트 IV)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))
    return iv + encrypted_data  # IV + 암호화된 데이터 반환

# AES256 복호화 bj <- Dc(bj, kbj)
def decrypt_with_aes(encrypted_data: bytes, key: bytes) -> bytes:
    if len(encrypted_data) < 16:
        raise ValueError("올바르지 않은 암호화 데이터입니다. IV가 존재하지 않습니다.")

    iv = encrypted_data[:16]  # IV 분리
    encrypted_data = encrypted_data[16:]  # 나머지 암호화된 데이터

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return decrypted_data  # 바이트 형식 반환

# 파일에서 원본 데이터를 읽어오기
def read_data_from_file(filename: str) -> bytes:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"파일 '{filename}'을 찾을 수 없습니다.")

    with open(filename, "rb") as file:  # 바이너리 모드로 읽기
        data = file.read()
    return data  # 바이트 형식 그대로 반환

# 암호화 or 복호화된 데이터를 파일로 저장 (바이너리 모드)
def save_data_to_file(data: bytes, filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)  # 폴더가 없으면 생성

    with open(filename, "wb") as file:  # 바이너리 모드로 저장
        file.write(data)  # 바이너리 데이터 저장
    # print(f"데이터가 파일 '{filename}'에 저장됨.")

# 파일에서 암호화된 데이터 불러오기
def load_encrypted_from_file(filename: str) -> bytes:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"파일 '{filename}'을 찾을 수 없습니다.")

    with open(filename, "rb") as file:  # 바이너리 모드로 읽기
        encrypted_data = file.read()
    # print(f"파일 '{filename}'에서 암호화된 데이터를 불러옴.")
    return encrypted_data

# 테스트 실행
if __name__ == "__main__":
    try:
        # AES 키 kbj 생성
        kbj = create_aes_key()

        # 원본 데이터 읽기 
        bj = read_data_from_file("../data/original_data.bin")  # 바이너리 파일 읽기

        # AES 암호화 Es(bj, kbj)
        encrypted_data = encrypt_with_aes(bj, kbj)
        print(f"암호화된 데이터 bj 길이: {len(encrypted_data)} bytes")

        # 암호화된 데이터를 파일로 저장 
        # 해당 파일을 IPFS에 업로드 필요
        encrypted_file = "../data/encrypted_data.enc"
        save_data_to_file(encrypted_data, encrypted_file)

        # 저장된 암호화된 데이터 불러오기
        loaded_encrypted_file = load_encrypted_from_file(encrypted_file)

        # AES 복호화 bj <- Dc(bj, kbj)
        decrypted_data = decrypt_with_aes(loaded_encrypted_file, kbj)
        print(f"복호화된 데이터 bj 길이: {len(decrypted_data)} bytes")

        # 복호화된 데이터를 파일로 저장
        # 해당 파일을 IoT 디바이스에 전송
        decrypted_file = "../data/decrypted_data.bin"
        save_data_to_file(decrypted_data, decrypted_file)

    except Exception as e:
        print(f"AES 오류 발생: {e}")
