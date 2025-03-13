# 블록체인에 데이터 저장 및 조회하는 코드
from web3 import Web3
import json
from config import CONTRACT_ADDRESS, ACCOUNT_ADDRESS, ACCOUNT_PRIVATE_KEY

# ✅ 블록체인 RPC 주소
BLOCKCHAIN_RPC_URL = "http://127.0.0.1:8545"

# ✅ Web3 인스턴스 생성
w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC_URL))

# ✅ 사용할 계정 설정 (Hardhat이나 Ganache에서 가져온 주소)
ACCOUNT_ADDRESS = ACCOUNT_ADDRESS  # 🟢 본인 계정 주소로 변경
PRIVATE_KEY = ACCOUNT_PRIVATE_KEY  # 🟢 해당 계정의 개인키

# ✅ 배포된 스마트 컨트랙트 주소 (배포 후 나온 주소 입력)
RAW_CONTRACT_ADDRESS = CONTRACT_ADDRESS  # 🟢 본인 컨트랙트 주소로 변경
CONTRACT_ADDRESS = w3.to_checksum_address(RAW_CONTRACT_ADDRESS)  # ✅ 체크섬 주소로 변환

# ✅ 스마트 컨트랙트 ABI (해당 스마트 컨트랙트의 ABI JSON 파일 필요)
with open("contract_abi.json") as f:
    contract_data = json.load(f)
    CONTRACT_ABI = contract_data.get("abi", [])  # "abi" 값만 가져오기
    # CONTRACT_ABI = json.load(f)
    
# ✅ ABI가 리스트인지 검증
if not isinstance(CONTRACT_ABI, list):
    raise TypeError("🚨 ABI는 리스트여야 합니다! JSON 파일을 확인하세요.")

# ✅ 컨트랙트 인스턴스 생성
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)


def send_data_to_blockchain(uid, update_hash):
    """블록체인에 업데이트 정보 저장"""
    try:
        nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

        # 🔹 스마트 컨트랙트 함수 호출
        tx = contract.functions.registerUpdate(
            uid,  # 업데이트 ID
            bytes.fromhex(update_hash.replace("0x", "")),  # SHA-3 해시값
            b"EncryptedKeyExample",  # 암호화된 키 (예제)
            b"SignatureExample",  # 서명 (예제)
            100  # 가격 (예제)
        ).build_transaction({
            "from": ACCOUNT_ADDRESS,
            "gas": 3000000,
            "gasPrice": w3.to_wei("10", "gwei"),
            "nonce": nonce
        })

        # 🔹 트랜잭션 서명 및 전송 (🚀 FIXED)
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"✅ 데이터 저장 트랜잭션 전송 완료! 해시: {tx_hash.hex()}")

        # 🔹 트랜잭션 완료 대기
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print("🔹 트랜잭션 성공!", receipt)

    except Exception as e:
        print(f"⚠ 블록체인 데이터 저장 오류: {e}")


def get_data_from_blockchain(uid):
    """블록체인에서 업데이트 정보 조회"""
    try:
        result = contract.functions.getUpdateDetails(uid).call()

        print("✅ 블록체인에서 가져온 데이터:")
        print(f"🔹 Update Hash: {result[0].hex()}")
        print(f"🔹 Encrypted Key: {result[1].hex()}")
        print(f"🔹 Signature: {result[2].hex()}")
        print(f"🔹 Price: {result[3]}")
        print(f"🔹 Created At: {result[4]}")

    except Exception as e:
        print(f"⚠ 블록체인 데이터 조회 오류: {e}")


if __name__ == "__main__":
    # 🔹 저장할 데이터
    TEST_UID = "test-update-001"
    TEST_UPDATE_HASH = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    # 🔹 블록체인에 데이터 저장
    send_data_to_blockchain(TEST_UID, TEST_UPDATE_HASH)

    # 🔹 저장된 데이터 조회
    get_data_from_blockchain(TEST_UID)