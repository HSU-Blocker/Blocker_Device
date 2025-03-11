import asyncio
from blockchain.blockchain_service import BlockChainService
from device.update_manager import UpdateManager
from ipfs.ipfs_service import IPFSClient
from config import BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, IPFS_API_ADDR, MANUFACTURER_PUBLIC_KEY, DEVICE_CPABE_SECRET_KEY

# CP-ABE 초기화 (가정)
from cpabe_init import CPABEInit
from cpabe_crypto import CPABECrypto

cpabe_init = CPABEInit()  # pairing_group='SS512'
cpabe, group, public_key = cpabe_init.get_cpabe_objects()
cpabe_crypto = CPABECrypto(cpabe, group, public_key)

# UpdateManager 관련 import
from device.update_manager import UpdateManager

# def main():
#     # 업데이트 매니저 생성
#     manager = UpdateManager(
#         rpc_url=BLOCKCHAIN_RPC_URL,
#         contract_address=CONTRACT_ADDRESS,
#         abi_path="contract_abi.json",
#         ipfs_addr=IPFS_API_ADDR,
#         ecdsa_public_key=MANUFACTURER_PUBLIC_KEY,  # 실제 파일 경로
#         cpabe_crypto=cpabe_crypto,
#         device_sk=DEVICE_CPABE_SECRET_KEY  # dict
#     )

#     # 테스트용 UID, CID
#     uid = "https://example.com/updates/v1.0"
#     ipfs_cid = "QmExampleCID"

#     # 업데이트 수행
#     try:
#         result_file = manager.perform_update(uid, ipfs_cid, "update.enc")
#         print("최종 복호화된 파일:", result_file)
#     except Exception as e:
#         print("업데이트 실패:", e)

# if __name__ == "__main__":
#     main()
async def main():
    """
    Web3 Listener를 실행하고 블록체인 이벤트를 감지하여 업데이트 수행
    """
    # 블록체인 서비스 및 IPFS 클라이언트 초기화
    blockchain_service = BlockChainService(BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, "contract_abi.json")
    ipfs_client = IPFSClient(IPFS_API_ADDR)

    # UpdateManager 초기화 (블록체인 서비스와 IPFS 클라이언트 연결)
    update_manager = UpdateManager(blockchain_service, ipfs_client, MANUFACTURER_PUBLIC_KEY, None, DEVICE_CPABE_SECRET_KEY)

    print("[Main] 블록체인 이벤트 리스너 시작...")

    # Web3 Listener 실행 (업데이트 이벤트 감지 → 업데이트 수행)
    await blockchain_service.listen_for_updates(update_manager)

if __name__ == "__main__":
    asyncio.run(main())