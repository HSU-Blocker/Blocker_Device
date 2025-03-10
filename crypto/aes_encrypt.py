import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

class AESEncrypt:
    def __init__(self, key: bytes):
        """
        AES 암호화 클래스 (CBC 모드)
        - key: 16, 24, 32바이트 길이의 AES 키
        """
        if len(key) not in (16, 24, 32):
            raise ValueError("AES 키는 16, 24, 32바이트여야 합니다.")
        self.key = key

    # Es(bj, kbj)
    def encrypt(self, data: bytes) -> bytes:
        """
        AES 암호화 수행
        - data: 바이트 형식의 원본 데이터
        - 반환값: IV + AES 암호화된 데이터
        """
        if not isinstance(data, bytes):
            raise ValueError("암호화할 데이터는 바이트 형식이어야 합니다.")

        iv = os.urandom(16)  # AES 블록 크기 (16바이트 IV)
        print(f"AES 암호화 키: {self.key}")
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))

        return iv + encrypted_data  # IV + 암호화된 데이터 반환

    @staticmethod
    def save_to_file(data: bytes, filename: str):
        """ 암호화된 데이터를 파일에 저장 """
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as file:
            file.write(data)
        print(f"암호화된 데이터가 '{filename}' 파일에 저장됨.")
