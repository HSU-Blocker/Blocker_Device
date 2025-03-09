import json
import os
from web3 import Web3

class BlockChainService:
    def __init__(self, rpc_url: str, contract_address: str, abi_path="contract_abi.json"):
        """
        :param rpc_url: 블록체인 RPC URL (Hardhat 노드 등)
        :param contract_address: 배포된 SoftwareUpdateManager 컨트랙트 주소
        :param abi_path: ABI JSON 파일 경로
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.isConnected():
            raise Exception(f"블록체인 노드({rpc_url})에 연결할 수 없습니다.")

        if not os.path.exists(abi_path):
            raise FileNotFoundError(f"ABI 파일({abi_path})이 존재하지 않습니다.")
        with open(abi_path, "r") as f:
            abi = json.load(f)

        self.contract = self.w3.eth.contract(address=contract_address, abi=abi)

    def get_update_metadata(self, uid: str):
        """
        updates(uid)를 조회하여 업데이트 구조체를 가져온다.
        (string uid, bytes32 updateHash, bytes encryptedKey, bytes signature,
         bool active, uint256 price, uint256 createdAt)

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
            raise Exception("Update is not active or does not exist.")

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

    def get_signature_only(self, uid: str):
        """
        updates(uid).signature 필드만 가져오는 간단한 예시
        """
        data = self.contract.functions.updates(uid).call()
        return data[3]  # signature
    
    
    # 업데이트 완료 시 블록체인에 보고 
    #