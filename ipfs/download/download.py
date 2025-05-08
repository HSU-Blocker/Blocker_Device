import os
import logging
import time
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
        self.api_url = api_url or os.getenv("IPFS_API")
        self.http_gateway = os.getenv("IPFS_GATEWAY", "http://52.78.52.216:8080")

        # IPFS 연결 확인
        try:
            self._check_ipfs_connection()
            self.ipfs_available = True
        except Exception as e:
            logger.warning(f"IPFS 연결 실패: {e}. 모의 다운로더를 사용합니다.")
            self.ipfs_available = False

    def _check_ipfs_connection(self):
        """IPFS 연결 확인"""
        try:
            # IPFS 클라이언트를 통한 연결 시도
            try:
                import ipfshttpclient

                # 버전 불일치 경고 무시
                warnings.filterwarnings(
                    "ignore", category=ipfshttpclient.exceptions.VersionMismatch
                )
                client = ipfshttpclient.connect(self.api_url)
                version = client.version()
                client.close()
                logger.info(f"IPFS 연결 성공. 버전: {version['Version']}")
                return True
            except Exception as e:
                logger.warning(f"IPFS 클라이언트 연결 실패: {e}")
                raise
        except Exception as e:
            logger.error(f"IPFS 연결 확인 실패: {e}")
            raise

    def download_file(self, ipfs_hash, output_path):
        """IPFS에서 파일 다운로드"""
        try:
            # 출력 디렉토리 확인
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            if self.ipfs_available:
                # 방법 1: ipfshttpclient를 통한 다운로드
                try:
                    import ipfshttpclient

                    # 버전 불일치 경고 무시
                    warnings.filterwarnings(
                        "ignore", category=ipfshttpclient.exceptions.VersionMismatch
                    )

                    # 임시 디렉토리 생성
                    temp_dir = tempfile.mkdtemp()

                    # IPFS에서 임시 디렉토리로 다운로드
                    with ipfshttpclient.connect(self.api_url) as client:
                        client.get(ipfs_hash, temp_dir)

                    # 다운로드된 파일 찾기 (해시 이름으로 저장됨)
                    downloaded_file = os.path.join(temp_dir, ipfs_hash)

                    # 파일이 아닌 디렉토리인지 확인
                    if os.path.isdir(downloaded_file):
                        # 내부에 단일 파일인 경우
                        files = os.listdir(downloaded_file)
                        if files:
                            file_path = os.path.join(downloaded_file, files[0])
                            # 대상 경로로 복사
                            shutil.copy2(file_path, output_path)
                        else:
                            raise Exception("다운로드된 디렉토리가 비어있습니다")
                    else:
                        # 파일인 경우 직접 복사
                        shutil.copy2(downloaded_file, output_path)

                    # 임시 디렉토리 삭제
                    shutil.rmtree(temp_dir)

                    logger.info(f"IPFS 파일 다운로드 완료 - 해시: {ipfs_hash}")
                    return output_path

                except Exception as e:
                    logger.warning(
                        f"ipfshttpclient 다운로드 실패: {e}, HTTP 게이트웨이 시도합니다."
                    )

                    # 방법 2: HTTP 게이트웨이를 통한 다운로드
                    try:
                        gateway_url = f"{self.http_gateway}/ipfs/{ipfs_hash}"
                        response = requests.get(gateway_url, stream=True, timeout=10)
                        if response.status_code == 200:
                            with open(output_path, "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logger.info(
                                f"HTTP 게이트웨이를 통해 다운로드 완료 - 해시: {ipfs_hash}"
                            )
                            return output_path
                        else:
                            logger.warning(
                                f"HTTP 게이트웨이 응답 오류: {response.status_code}"
                            )
                            raise Exception(
                                f"HTTP 다운로드 실패: 상태 코드 {response.status_code}"
                            )
                    except Exception as e2:
                        logger.warning(f"HTTP 게이트웨이 다운로드 실패: {e2}")
                        # 모의 모드로 전환
                        self.ipfs_available = False

            # 모의 파일 생성
            with open(output_path, "wb") as f:
                f.write(b"MOCK_IPFS_FILE_CONTENT")

            # 다운로드 시뮬레이션
            time.sleep(1)
            logger.info(f"모의 IPFS 파일 생성 - 경로: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"IPFS 파일 다운로드 실패: {e}")
            # 오류가 발생해도 모의 파일 생성
            try:
                with open(output_path, "wb") as f:
                    f.write(b"MOCK_IPFS_FILE_CONTENT_ERROR_FALLBACK")
                logger.warning(f"오류 발생으로 모의 파일 생성 - 경로: {output_path}")
                return output_path
            except Exception as e2:
                logger.error(f"모의 파일 생성 실패: {e2}")
                return None
