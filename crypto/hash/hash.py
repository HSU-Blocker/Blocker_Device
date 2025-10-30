import hashlib
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class HashTools:
    """파일 해시 계산 및 검증을 위한 도구"""

    @staticmethod
    def sha3_hash_file(file_path, chunk_size=8192):
        """SHA-3 (SHA3-256) 알고리즘을 사용하여 파일의 해시값 계산"""
        try:
            hash_obj = hashlib.sha3_256()

            with open(file_path, "rb") as f:
                chunk = f.read(chunk_size)
                while chunk:
                    print(f"Chunk Read ({len(chunk)} bytes): {chunk[:10]}...")  # 로그 추가
                    hash_obj.update(chunk)
                    chunk = f.read(chunk_size)

            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"파일 SHA3 해시 계산 중 오류: {e}")
            return None