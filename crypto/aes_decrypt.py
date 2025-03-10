import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

class AESDecrypt:
    def __init__(self, key: bytes):
        """
        AES 복호화 클래스 (CBC 모드)
        - key: 16, 24, 32바이트 길이의 AES 키
        """
        if len(key) not in (16, 24, 32):
            raise ValueError("AES 키는 16, 24, 32바이트여야 합니다.")
        self.key = key

    # Dc(bj, kbj)
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        AES 복호화 수행
        - encrypted_data: IV + 암호화된 데이터
        - 반환값: 복호화된 원본 데이터
        """
        if len(encrypted_data) < 16:
            raise ValueError("올바르지 않은 암호화 데이터입니다. (IV 없음)")

        iv = encrypted_data[:16]  # IV 분리
        encrypted_data = encrypted_data[16:]

        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        
        return decrypted_data  # 바이트 형식 반환

    @staticmethod
    def load_from_file(filename: str) -> bytes:
        """ 파일에서 암호화된 데이터를 읽어오기 """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"파일 '{filename}'을 찾을 수 없습니다.")

        with open(filename, "rb") as file:
            return file.read()
