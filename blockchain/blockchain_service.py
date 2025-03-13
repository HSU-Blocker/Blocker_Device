import json
import asyncio
import logging
from web3 import AsyncWeb3
from web3.providers.persistent import WebSocketProvider

class BlockChainService:
    def __init__(self, rpc_url: str, contract_address: str, abi_path="contract_abi.json"):
        """
        WebSocket Provider를 통한 비동기 블록체인 서비스 초기화
        :param rpc_url: 블록체인 WebSocket URL
        :param contract_address: 배포된 SoftwareUpdateManager 컨트랙트 주소
        :param abi_path: ABI JSON 파일 경로
        !! 고려해볼것
        블록체인 RPC만으로 가능한 작업 (스마트 컨트랙트 주소 필요 없음)
        블록체인 RPC는 노드와 직접 통신하는 인터페이스이기 때문에, 기본적인 블록체인 데이터 조회(read) 작업은 가능함.
        """
        self.logger = logging.getLogger("BlockChainService")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())

        # ✅ WebSocket을 통한 AsyncWeb3 연결
        self.w3 = AsyncWeb3(WebSocketProvider(rpc_url))

        # WebSocket 연결 확인
        if not asyncio.run(self.w3.is_connected()):
            raise Exception(f"블록체인 WebSocket({rpc_url})에 연결할 수 없습니다.")

        # json에서 ABI만 로드
        with open(abi_path, "r") as f:
            abi = json.load(f).get("abi", [])

        # 스마트 컨트랙트 설정
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)

    async def listen_for_updates(self, update_manager):
        """
        블록체인 이벤트 리스너 실행 (Web3 Listener)
        """
        print("[BlockChainService] 블록체인 업데이트 이벤트 대기 중...")

        # 스마트 컨트랙트 이벤트 구독 (UpdateRegistered 이벤트 감지)
        subscription_id = await self.w3.eth.subscribe("logs", {
            "address": self.contract.address
        })
        print(f"🛰 이벤트 구독 시작 (subscription_id: {subscription_id})")

        try:
            async for event in self.w3.socket.process_subscriptions():
                print(f"🔔 새 업데이트 이벤트 감지: {event}")

                # 이벤트에서 UID 가져오기
                update_uid = event["args"]["uid"]
                print(f"🔍 업데이트 UID: {update_uid}")

                # 업데이트 실행
                await update_manager.perform_update(update_uid)

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