class CPABECrypto:
    def __init__(self, cpabe, group, public_key):
        self.cpabe = cpabe
        self.group = group
        self.public_key = public_key

    # CP-ABE 암호화
    # Ec(PKc, kbj, A)
    def encrypt(self, target, policy):
        try:
            encrypted_result = self.cpabe.encrypt(self.public_key, target, policy)
            print("CP-ABE 암호문 생성 완료")
            return encrypted_result
        except Exception as e:
            print(f"CP-ABE 암호화 실패: {e}")
            return None

    # CP-ABE 복호화화
    # kbj <- Dc(PKc, encrypted_result, SKd)
    def decrypt(self, device_secret_key, encrypted_data):
        """CP-ABE 복호화"""
        try:
            decrypted_result = self.cpabe.decrypt(self.public_key, device_secret_key, encrypted_data)

            if decrypted_result is None:
                print("CP-ABE 복호화 실패: 접근 정책이 충족되지 않음")
                return None

            print(f"CP-ABE로 복호화된 메시지: {decrypted_result}")
            return decrypted_result
        except Exception as e:
            print(f"CP-ABE 복호화 중 오류 발생: {e}")
            return None
