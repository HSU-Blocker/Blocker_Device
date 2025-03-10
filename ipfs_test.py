from ipfs.ipfs_service import IPFSClient  # IPFSClient 클래스가 정의된 파일을 import
import os

# IPFSClient 인스턴스 생성 (기본 게이트웨이: https://ipfs.io/ipfs/)
ipfs_client = IPFSClient()

# 테스트할 CID (공개된 IPFS 파일)
test_cid = "QmciVWJu4EopjBWay3g4s7urE6TaocszSc2TKwf78zQb6H"

# 다운로드 실행
downloaded_file = ipfs_client.download_file(test_cid, "downloaded_readme.txt")

# 다운로드된 파일이 정상적으로 존재하는지 확인
if os.path.exists(downloaded_file):
    print(f"[ipfs_test] 다운로드 성공! 파일 경로: {downloaded_file}")

    # 파일 내용 일부 출력 (첫 200자 미리보기)
    with open(downloaded_file, "r", encoding="utf-8") as file:
        preview = file.read(200)
        print("\n [ipfs_test] 파일 내용 (미리보기):")
        print(preview)
else:
    print("[ipfs_test] 다운로드 실패! 파일이 존재하지 않습니다.")