from charm.toolbox.pairinggroup import GT

class CPABEDecrypt:
    def __init__(self, cpabe, group, public_key):
        self.cpabe = cpabe
        self.group = group
        self.public_key = public_key

    # CP-ABE 복호화 kbj <- Dc(PKc, kbj, SKd)
    def decrypt(self, device_secret_key, encrypted_data):
        """
        CP-ABE 복호화 수행
        - device_secret_key: 사용자(디바이스)의 CP-ABE 개인 키
        - encrypted_data: 암호화된 데이터 kbj
        """
        try:
            if not isinstance(encrypted_data, dict):
                print("CP-ABE 복호화 실패: `encrypted_data`가 올바른 형식이 아닙니다.")
                return None

            # 역직렬화 전 데이터 확인
            print(f"역직렬화 전 데이터 타입 확인: {type(encrypted_data)}")
            print(f"`C` 타입: {type(encrypted_data.get('C'))}")
            print(f"`C_tilde` 타입: {type(encrypted_data.get('C_tilde'))}")
            print(f"`policy` 타입: {type(encrypted_data.get('policy'))}")

            # CP-ABE 암호문 역직렬화
            deserialized_data = {}
            for k, v in encrypted_data.items():
                if isinstance(v, bytes):  # GT 요소인 경우
                    deserialized_data[k] = self.group.deserialize(v)
                else:
                    deserialized_data[k] = v  # GT 요소가 아니면 그대로 저장

            print("CP-ABE 암호문 역직렬화 완료")

            # `policy` 타입 강제 변환 (문자열 유지)
            if "policy" in deserialized_data and not isinstance(deserialized_data["policy"], str):
                deserialized_data["policy"] = str(deserialized_data["policy"])

            # CP-ABE 복호화 수행
            decrypted_result = self.cpabe.decrypt(self.public_key, device_secret_key, deserialized_data)
            print(f"CP-ABE 복호화 결과: {decrypted_result}")

            # 복호화 실패 시 예외 처리
            if decrypted_result is None:
                print("CP-ABE 복호화 실패: 복호화 결과가 None")
                return None
            
            if isinstance(decrypted_result, bool):
                print("CP-ABE 복호화 실패: 접근 정책이 충족되지 않음")
                return None

            return decrypted_result
        except Exception as e:
            print(f"CP-ABE 복호화 중 오류 발생: {e}")
            return None
