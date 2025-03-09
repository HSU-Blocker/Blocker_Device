# import os
# from Crypto.Random import get_random_bytes

# class AESInit:
#     # AES 초기화
#     # 256비트 키 기본, param key_size: 16(128비트), 24(192비트), 32(256비트) 선택 가능
#     def __init__(self, key_size=32):
#         self.key_size = key_size
#         self._aes_key = None

#     # AES 대칭 키 kbj 생성
#     def create_aes_key(self):
#         self._aes_key = get_random_bytes(self.key_size)
#         print(f"AES Key ({self.key_size * 8}-bit) 생성 완료: {self._aes_key.hex()}")
#         return self._aes_key

#     @property
#     def aes_key(self):
#         if self._aes_key is None:
#             raise ValueError("AES 키가 아직 생성되지 않았습니다.")
#         return self._aes_key

#     # kbj를 파일로 저장
#     def save_key_to_file(self, filename="aes_key.bin"):
#         if self._aes_key is None:
#             raise ValueError("저장할 AES 키가 없습니다.")
        
#         os.makedirs(os.path.dirname(filename), exist_ok=True)
#         with open(filename, "wb") as file:
#             file.write(self._aes_key)
#         print(f"AES 키 kbj가 '{filename}' 파일에 저장됨.")

#     # kbj를 파일에서 불러오기
#     def load_key_from_file(self, filename="aes_key.bin"):
#         """"""
#         if not os.path.exists(filename):
#             raise FileNotFoundError(f"파일 '{filename}'을 찾을 수 없습니다.")
        
#         with open(filename, "rb") as file:
#             self._aes_key = file.read()
#         print(f"AES 키 kbj가 '{filename}' 파일에서 로드됨.")
#         return self._aes_key
