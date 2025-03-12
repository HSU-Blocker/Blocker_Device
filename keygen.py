# import os
# from ecdsa import SigningKey, VerifyingKey, NIST256p

# # 개인키, 공개키 생성
# def keygen(private_key_path, public_key_path):
#     """
#     ECDSA KeyGen 함수: 제조사의 공개 키(PK)와 개인 키(SK)를 생성하고 저장
#     - private_key_path: 개인 키 저장 경로
#     - public_key_path: 공개 키 저장 경로
#     """
#     # 개인 키 & 공개 키 생성
#     signing_key = SigningKey.generate(curve=NIST256p)  # 제조사 개인 키 (SK)
#     verifying_key = signing_key.verifying_key  # 제조사 공개 키 (PK)

#     # 키를 PEM 형식으로 저장
#     with open(private_key_path, "wb") as f:s
#         f.write(signing_key.to_pem())
    
#     with open(public_key_path, "wb") as f:
#         f.write(verifying_key.to_pem())

#     print(f"키 저장 완료: {private_key_path}, {public_key_path}")
#     return signing_key, verifying_key

# # 실행 예제 
# if __name__ == "__main__":
#     keygen()  # 기본 경로로 키 생성 및 저장