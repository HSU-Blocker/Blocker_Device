import base64
from charm.toolbox.pairinggroup import PairingGroup, GT

class CPABECrypto:
    def __init__(self, cpabe, group, public_key):
        self.cpabe = cpabe
        self.group = group
        self.public_key = public_key

    # CP-ABE 암호화
    # Ec(PKc, kbj, A)
    def encrypt(self, target, policy):
        try:
            # GT 그룹 요소 변환 (AES 키 kbj를 GT 요소로 변환)
            if isinstance(target, bytes):
                target_value = int.from_bytes(target, "big")  # bytes → int 변환
                target = self.group.init(GT, target_value)

            encrypted_result = self.cpabe.encrypt(self.public_key, target, policy)
            if encrypted_result is None:
                print("CP-ABE 암호화 실패: 결과가 None")
                return None

            # GT 요소 타입 비교 수정
            serialized_result = {
                k: self.group.serialize(v) if isinstance(v, type(self.group.random(GT))) else v
                for k, v in encrypted_result.items()
            }
            print("CP-ABE 암호문 직렬화 완료")
            return serialized_result
        except Exception as e:
            print(f"CP-ABE 암호화 실패: {e}")
            return None

    # CP-ABE 복호화
    # kbj <- Dc(PKc, kbj,SKd)
    def decrypt(self, device_secret_key, encrypted_data):
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

            # 복호화 수행
            decrypted_result = self.cpabe.decrypt(self.public_key, device_secret_key, deserialized_data)
            print(f"CP-ABE 복호화 결과: {decrypted_result}")

            # 복호화 실패 시 예외 처리
            if decrypted_result is None:
                print("CP-ABE 복호화 실패: 복호화 결과가 None")
                return None

            # # GT 그룹 요소인 경우 → bytes 변환
            # if isinstance(decrypted_result, type(self.group.random(GT))):  # GT 요소 타입 비교
            #     decrypted_bytes = self.group.serialize(decrypted_result)
            #     print(f"CP-ABE 복호화 성공 (GT 요소 변환): {decrypted_bytes}")
            #     return decrypted_bytes

            # # 이미 bytes 형태라면 그대로 반환
            # if isinstance(decrypted_result, bytes):
            #     print(f"CP-ABE 복호화 성공 (bytes 반환): {decrypted_result.hex()}")
            #     return decrypted_result

            return decrypted_result
        except Exception as e:
            print(f"CP-ABE 복호화 중 오류 발생: {e}")
            return None
