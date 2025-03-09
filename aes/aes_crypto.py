import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

class AESCipher:
    # AES 암호화 클래스 (CBC 모드)
    def __init__(self, key: bytes):
        if len(key) not in (16, 24, 32):
            raise ValueError("AES 키는 16, 24, 32바이트여야 합니다.")
        self.key = key

    # AES256 암호화
    # Es(bj, kbj)
    def encrypt(self, data: bytes) -> bytes:
        if not isinstance(data, bytes):
            raise ValueError("암호화할 데이터는 바이트 형식이어야 합니다.")

        iv = os.urandom(16)  # AES 블록 크기 (16바이트 IV)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))
        return iv + encrypted_data  # IV + 암호화된 데이터 반환

    # AES256 복호화
    # bj <- Ds(bj, kbj)
    def decrypt(self, encrypted_data: bytes) -> bytes:
        if len(encrypted_data) < 16:
            raise ValueError("올바르지 않은 암호화 데이터입니다. (IV 없음)")

        iv = encrypted_data[:16]  # IV 분리
        encrypted_data = encrypted_data[16:]

        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return decrypted_data  # 바이트 형식 반환

    # 파일에서 데이터를 읽어오기 (바이너리 모드)
    @staticmethod
    def read_data_from_file(filename: str) -> bytes:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"⛔ 파일 '{filename}'을 찾을 수 없습니다.")

        with open(filename, "rb") as file:
            data = file.read()
        return data  # 바이트 형식 그대로 반환

    # 암호화 또는 복호화된 데이터를 파일로 저장
    @staticmethod
    def save_data_to_file(data: bytes, filename: str):
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "wb") as file:
            file.write(data)
        print(f"📂 데이터가 '{filename}' 파일에 저장됨.")
