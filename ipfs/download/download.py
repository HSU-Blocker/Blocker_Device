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
        # 기본값: 로컬 노드 (환경변수로 재정의 가능)
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

    def download_file(self, ipfs_hash, save_dir, uid):
        """
        IPFS에서 파일 다운로드 후 확장자 복원하여 updates/<uid>.<확장자> 로 저장
        :param ipfs_hash: 다운로드할 CID
        :param save_dir: 저장할 디렉토리 (예: updates/)
        :param uid: 저장 시 사용할 이름 (ex: forward_v1.5.0)
        :return: 최종 저장 경로
        """
        if not self.ipfs_available:
            raise ConnectionError("🚨 IPFS API 연결 불가. 다운로드를 수행할 수 없습니다.")

        os.makedirs(save_dir, exist_ok=True)

        try:
            import ipfshttpclient
            warnings.filterwarnings("ignore", category=ipfshttpclient.exceptions.VersionMismatch)

            # 임시 디렉토리 생성 후 파일 다운로드
            temp_dir = tempfile.mkdtemp()
            with ipfshttpclient.connect(self.api_url) as client:
                client.get(ipfs_hash, temp_dir)

            downloaded_path = os.path.join(temp_dir, ipfs_hash)
            logger.info(f"다운로드 받은 경로: {downloaded_path}")

            # CID가 디렉토리일 경우 → 내부 파일 접근
            if os.path.isdir(downloaded_path):
                files = os.listdir(downloaded_path)
                if not files:
                    raise Exception("다운로드된 디렉토리가 비어있습니다.")
                downloaded_file = os.path.join(downloaded_path, files[0])
                file_name = files[0]
                logger.info(f"실제 다운로드된 파일명: {file_name}")
            else:
                # 디렉토리가 아니면 CID 그대로 파일 취급
                downloaded_file = downloaded_path
                file_name = ipfs_hash
                logger.info("⚠️ 원래 파일명 정보를 찾지 못했습니다. CID로 저장합니다.")

            # 확장자 복원: 원래 파일명에서 확장자 그대로 가져오기
            _, ext = os.path.splitext(file_name)
            if file_name.count(".") > 1:
                # .py.enc 같은 다중 확장자 처리
                original_ext = ".".join(file_name.split(".")[1:])
                original_ext = "." + original_ext
            else:
                original_ext = ext or ".bin"

            # 최종 저장 경로
            final_path = os.path.join(save_dir, f"{uid}{original_ext}")
            shutil.copy2(downloaded_file, final_path)
            shutil.rmtree(temp_dir)

            logger.info(f"✅ IPFS 파일 다운로드 완료 - 저장 경로: {final_path}")
            return final_path

        except Exception as e:
            # 실패 시 게이트웨이 fallback
            logger.warning(f"⚠️ ipfshttpclient 다운로드 실패: {e}, 게이트웨이로 재시도합니다.")
            gateway_url = f"{self.http_gateway}/ipfs/{ipfs_hash}"
            response = requests.get(gateway_url, stream=True, timeout=10)
            if response.status_code == 200:
                final_path = os.path.join(save_dir, f"{uid}.bin")
                with open(final_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"✅ 게이트웨이 다운로드 완료 - 저장 경로: {final_path}")
                return final_path
            else:
                raise Exception(f"HTTP 다운로드 실패: 상태 코드 {response.status_code}")
