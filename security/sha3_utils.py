import hashlib

class SHA3Utils:

    # 해시값 생성
    @staticmethod
    def compute_sha3_hash(file_path):
        """
        주어진 파일의 SHA3-256 해시를 생성하여 반환

        :param file_path: 해시를 생성할 파일의 경로
        :return: SHA3-256 해시 (16진수 문자열)
        """
        hasher = hashlib.sha3_256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(4096):  # 4KB 단위로 읽기
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {file_path}")
            return None

    # um에서 다운받은 파일과 IPFS에서 다운 받은 파일의 해시 값 검증
    @staticmethod
    def verify_sha3_hash(hEbj, encrypted_aes_file):
        computed_hash = SHA3Utils.compute_sha3_hash(encrypted_aes_file)
        if computed_hash is None:
            return False

        is_match = computed_hash == hEbj
        if is_match:
            print("SHA3-256 해시 검증 성공")
        else:
            print("SHA3-256 해시 검증 실패")
            print(f"um에 포함된 hEbj: {hEbj}")
            print(f"IPFS에서 다운받은 파일의 해시값: {computed_hash}")

        return is_match
