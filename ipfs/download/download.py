import os
import logging
import tempfile
import requests
import warnings
import shutil

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPFSDownloader:
    """IPFS에서 파일 다운로드하는 클래스"""

    def __init__(self, api_url=None):
        """IPFS 다운로더 초기화"""
        self.api_url = api_url or os.getenv("IPFS_API", "http://127.0.0.1:5001")
        self.http_gateway = os.getenv("IPFS_GATEWAY", "http://127.0.0.1:8080")

        # IPFS 연결 확인
        self.ipfs_available = self._check_ipfs_connection()

    def _check_ipfs_connection(self):
        """IPFS API 연결 확인"""
        try:
            import ipfshttpclient
            # 버전 불일치 경고 무시
            warnings.filterwarnings(
                "ignore", category=ipfshttpclient.exceptions.VersionMismatch
            )
            client = ipfshttpclient.connect(self.api_url)
            version = client.version()
            client.close()
            logger.info(f"✅ IPFS 연결 성공. 버전: {version['Version']}")
            return True
        except Exception as e:
            logger.error(f"🚨 IPFS 연결 실패: {e}")
            return False

    def download_file(self, ipfs_hash, output_path):
        """IPFS에서 파일 다운로드"""
        if not self.ipfs_available:
            raise ConnectionError("🚨 IPFS API 연결 불가. 다운로드를 수행할 수 없습니다.")

        # 출력 디렉토리 확인
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 1. ipfshttpclient로 다운로드 시도
        try:
            import ipfshttpclient
            warnings.filterwarnings(
                "ignore", category=ipfshttpclient.exceptions.VersionMismatch
            )

            temp_dir = tempfile.mkdtemp()
            with ipfshttpclient.connect(self.api_url) as client:
                client.get(ipfs_hash, temp_dir)

            downloaded_file = os.path.join(temp_dir, ipfs_hash)

            if os.path.isdir(downloaded_file):
                files = os.listdir(downloaded_file)
                if not files:
                    raise Exception("다운로드된 디렉토리가 비어있습니다.")
                shutil.copy2(os.path.join(downloaded_file, files[0]), output_path)
            else:
                shutil.copy2(downloaded_file, output_path)

            shutil.rmtree(temp_dir)
            logger.info(f"✅ IPFS 파일 다운로드 완료 - 해시: {ipfs_hash}")
            return output_path

        except Exception as e:
            logger.warning(f"⚠️ ipfshttpclient 다운로드 실패: {e}, 게이트웨이로 재시도합니다.")

            # 2. HTTP 게이트웨이로 다운로드
            gateway_url = f"{self.http_gateway}/ipfs/{ipfs_hash}"
            response = requests.get(gateway_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"✅ 게이트웨이 다운로드 완료 - 해시: {ipfs_hash}")
                return output_path
            else:
                raise Exception(f"HTTP 다운로드 실패: 상태 코드 {response.status_code}")
