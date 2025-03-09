import ipfshttpclient
import os
from config import IPFS_API_ADDR

class IPFSClient:
    def __init__(self):
		    # IPFS 노드/게이트웨이에 연결
        self.client = ipfshttpclient.connect(IPFS_API_ADDR)

    def download_file(self, cid, target_path="update.enc"):
        """
        IPFS에서 CID로 파일을 다운로드하여 target_path에 저장
        """
        # ipfshttpclient의 get()은 CID 기반으로 폴더/파일을 가져옴
        # 만약 CID가 단일 파일이면 target_path로 저장
        self.client.get(cid, target=target_path)
        # 실제로는 CID가 폴더 형태면 다른 처리가 필요할 수도 있음
        return target_path # 어떤 경로에 파일이 저장되었는지 반환