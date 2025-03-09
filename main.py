import sys
import os
from config import BLOCKCHAIN_RPC_URL, CONTRACT_ADDRESS, IPFS_API_ADDR, MANUFACTURER_PUBLIC_KEY, DEVICE_CPABE_SECRET_KEY

# CP-ABE 초기화 (가정)
from cpabe_init import CPABEInit
from cpabe_crypto import CPABECrypto

cpabe_init = CPABEInit()  # pairing_group='SS512'
cpabe, group, public_key = cpabe_init.get_cpabe_objects()
cpabe_crypto = CPABECrypto(cpabe, group, public_key)

# UpdateManager 관련 import
from device.update_manager import UpdateManager

def main():
    # 업데이트 매니저 생성
    manager = UpdateManager(
        rpc_url=BLOCKCHAIN_RPC_URL,
        contract_address=CONTRACT_ADDRESS,
        abi_path="contract_abi.json",
        ipfs_addr=IPFS_API_ADDR,
        ecdsa_public_key=MANUFACTURER_PUBLIC_KEY,  # 실제 파일 경로
        cpabe_crypto=cpabe_crypto,
        device_sk=DEVICE_CPABE_SECRET_KEY  # dict
    )

    # 테스트용 UID, CID
    uid = "https://example.com/updates/v1.0"
    ipfs_cid = "QmExampleCID"

    # 업데이트 수행
    try:
        result_file = manager.perform_update(uid, ipfs_cid, "update.enc")
        print("최종 복호화된 파일:", result_file)
    except Exception as e:
        print("업데이트 실패:", e)

if __name__ == "__main__":
    main()