import requests
import os

class IPFSClient:
    def __init__(self, gateway_url="https://ipfs.io/ipfs/"):
        """
        :param gateway_url: IPFS 게이트웨이 URL (기본: https://ipfs.io/ipfs/)
        """
        self.gateway_url = gateway_url

    def download_file(self, cid, target_path="update.enc"):
        """
        IPFS에서 CID를 사용하여 파일을 다운로드하여 target_path에 저장.
        """
        url = f"{self.gateway_url}{cid}"
        print(f"[ipfs_service] url : {url}");
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            # 다운로드한 파일을 지정된 경로에 저장
            with open(target_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            print(f"[ipfs_service] 다운로드 완료: {target_path}")
            return target_path
        else:
            raise Exception(f"[ipfs_service] 다운로드 실패! 상태 코드: {response.status_code}")

