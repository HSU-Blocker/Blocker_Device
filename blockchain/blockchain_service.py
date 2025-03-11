import json
import asyncio
from web3 import Web3
from web3.middleware import geth_poa_middleware

class BlockChainService:
    def __init__(self, rpc_url: str, contract_address: str, abi_path="contract_abi.json"):
        """
        Web3 Provider 연결
        :param rpc_url: 블록체인 RPC URL (Hardhat 노드 등)
        :param contract_address: 배포된 SoftwareUpdateManager 컨트랙트 주소
        :param abi_path: ABI JSON 파일 경로
        """
        self.w3 = Web3(Web3.WebsocketProvider(rpc_url))  # WebSocket으로 연결
        if not self.w3.isConnected():
            raise Exception(f"블록체인 노드({rpc_url})에 연결할 수 없습니다.")

        # ABI 로드
        with open(abi_path, "r") as f:
            abi = json.load(f)
            
        # if not os.path.exists(abi_path):
        #     raise FileNotFoundError(f"ABI 파일({abi_path})이 존재하지 않습니다.")
        # with open(abi_path, "r") as f:
        #     abi = json.load(f)
        
        # 스마트 컨트랙트 설정
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)

    async def listen_for_updates(self, update_manager):
        """
        블록체인 이벤트 리스너 실행 (Web3 Listener)
        """
        print("[BlockChainService] 블록체인 업데이트 이벤트 대기 중...")

        event_filter = self.contract.events.UpdateRegistered.create_filter(fromBlock="latest")

        # Web3 Listener를 통해 이벤트 스트리밍
        while True:
            try:
                for event in event_filter.get_new_entries():
                    update_uid = event["args"]["uid"]
                    print(f"🔔 새 업데이트 감지! UID: {update_uid}")

                    # 업데이트 실행
                    await update_manager.perform_update(update_uid)

                await asyncio.sleep(0.1)  # 시스템 부담 최소화
            except Exception as e:
                print(f"⚠ Web3 Listener 오류 발생: {e}")
                await asyncio.sleep(1)  # 오류 발생 시 1초 대기 후 재시도

    def get_update_metadata(self, uid: str):
        """
        블록체인에서 업데이트 정보를 조회하여 반환
        :return: {
            "uid": str,
            "updateHash": bytes32,
            "encryptedKey": bytes,
            "signature": bytes,
            "active": bool,
            "price": int,
            "createdAt": int
        }
        """
        # 'updates'는 public mapping 이므로 자동 getter 존재
        # Solidity struct Update:
        #   (uid, updateHash, encryptedKey, signature, active, price, createdAt)
        data = self.contract.functions.updates(uid).call()
        # data는 튜플 형태로 반환
        #   data[0] = uid (string)
        #   data[1] = updateHash (bytes32)
        #   data[2] = encryptedKey (bytes)
        #   data[3] = signature (bytes)
        #   data[4] = active (bool)
        #   data[5] = price (uint256)
        #   data[6] = createdAt (uint256)

        if not data[4]:  # active == false
            raise Exception("업데이트가 비활성화 상태거나 존재하지 않습니다.")

        result = {
            "uid": data[0],
            "updateHash": data[1],
            "encryptedKey": data[2],
            "signature": data[3],
            "active": data[4],
            "price": data[5],
            "createdAt": data[6],
        }
        return result

    # def get_signature_only(self, uid: str):
    #     """
    #     updates(uid).signature 필드만 가져오는 간단한 예시
    #     """
    #     data = self.contract.functions.updates(uid).call()
    #     return data[3]  # signature
    
    
    # 업데이트 완료 시 블록체인에 보고 
    #