import base64
from charm.toolbox.pairinggroup import GT

class CPABEEncrypt:
    def __init__(self, cpabe, group, public_key):
        self.cpabe = cpabe
        self.group = group
        self.public_key = public_key

    # CP-ABE 암호화 Ec(PKc, kbj, SKd)
    def encrypt(self, target, policy):
        """
        CP-ABE 암호화 수행
        - target: 암호화할 데이터 (AES 키 등)
        - policy: 접근 정책 (예: "((ATTR1 and ATTR2) or (ATTR3 and ATTR4))")
        """
        try:
            # GT 그룹 요소 변환 (AES 키 kbj를 GT 요소로 변환)
            if isinstance(target, bytes):
                target_value = int.from_bytes(target, "big")  # bytes → int 변환
                target = self.group.init(GT, target_value)

            # CP-ABE 암호화 수행
            encrypted_result = self.cpabe.encrypt(self.public_key, target, policy)
            if encrypted_result is None:
                print("CP-ABE 암호화 실패: 결과가 None")
                return None

            # 암호문 직렬화 (GT 요소 변환)
            serialized_result = {
                k: self.group.serialize(v) if isinstance(v, type(self.group.random(GT))) else v
                for k, v in encrypted_result.items()
            }
            print("CP-ABE 암호문 직렬화 완료")
            return serialized_result
        except Exception as e:
            print(f"CP-ABE 암호화 실패: {e}")
            return None
