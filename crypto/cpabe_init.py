from charm.toolbox.pairinggroup import PairingGroup, GT
from charm.schemes.abenc.abenc_bsw07 import CPabe_BSW07
from charm.toolbox.secretutil import SecretUtil

class CPABEInit:
    def __init__(self, pairing_group='SS512'):
        # CP-ABE 시스템 초기화
        self._group = PairingGroup(pairing_group)
        self._cpabe = CPabe_BSW07(self._group)
        self._util = SecretUtil(self._group)

        # 공개 파라미터 PKc, 마스터키 생성
        self._public_key, self._master_key = self._cpabe.setup()

        # 생성된 사용자 키를 저장할 딕셔너리
        self._user_keys = {}

    @property
    def public_key(self):
        return self._public_key

    @property
    def group(self):
        return self._group

    # CP-ABE 키 생성
    def generate_secret_key(self, user_id, attributes):
        """사용자 속성 기반 개인 키 생성"""
        try:
            if user_id in self._user_keys:
                return self._user_keys[user_id]

            user_secret_key = self._cpabe.keygen(self._public_key, self._master_key, attributes)
            self._user_keys[user_id] = user_secret_key
            print(f"CP-ABE 키 생성 완료, 사용자 user_id: {user_id}")
            return user_secret_key
        except Exception as e:
            print(f"CP-ABE 키 생성 실패: {e}")
            return None

    def get_cpabe_objects(self):
        """CP-ABE 관련 객체 반환"""
        return self._cpabe, self._group, self._public_key
