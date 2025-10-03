from web3 import Web3, AsyncWeb3
import os
import json
import time
import logging
from dotenv import load_dotenv
import sys
import threading
import base64
from hashlib import sha256
from charm.core.engine.util import objectToBytes, bytesToObject

from crypto.symmetric.symmetric import SymmetricCrypto
from crypto.hash.hash import HashTools
from ipfs.download.download import IPFSDownloader
from crypto.cpabe.cpabe import CPABETools

import requests
MANUFACTURER_API_URL = os.getenv("MANUFACTURER_API_URL")

# 프로젝트 루트 디렉토리 추가
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
KEY_DIR = os.path.join(current_dir, "keys") #SKd 저장 폴더

class IoTDeviceClient:
    """IoT 기기 소프트웨어 업데이트 클라이언트"""

    def __init__(self, device_id, model, serial, version, notification_callback=None):
        """IoT 클라이언트 초기화"""
        # 장치 속성 설정
        self.device_id = device_id
        self.attributes = {"model": model, "serial": serial, "version": version}
        self.attributes_list = [
            f"model:{model}",
            f"serial:{serial}",
            f"version:{version}",
        ]
        self.notification_callback = notification_callback

        # 웹3 연결 설정
        self.web3_socket_provider = os.getenv("WEB3_WS_PROVIDER")
        self.web3_http_provider = os.getenv("WEB3_PROVIDER")
        self.owner_address = os.getenv("OWNER_ADDRESS")
        self.owner_private_key = os.getenv("OWNER_PRIVATE_KEY")

        # 계정 설정 확인
        if not self.owner_address or not self.owner_private_key:
            raise ValueError(
                "OWNER_ADDRESS 또는 OWNER_PRIVATE_KEY가 환경 변수에 설정되지 않았습니다"
            )

        # Web3 연결
        self.web3_http = Web3(Web3.HTTPProvider(self.web3_http_provider)) # API 조회용
        self.web3_socket = None # WebSocket 연결용

        # 연결 확인
        try:
            if not self.web3_http.is_connected():
                logger.warning(f"이더리움 노드 연결 실패: {self.web3_http_provider}")
                # 오류를 발생시키지 않고 경고만 기록
            else:
                logger.info(f"[init] Web3_http 연결 성공: {self.web3_http_provider}")
        except Exception as e:
            logger.warning(f"[init] Web3_http 연결 확인 오류: {e}")
            # 연결이 안 되어도 계속 진행 (오프라인 테스트용)

        # CP-ABE 초기화
        self.cpabe = CPABETools()
        self.group = self.cpabe.get_group()

        # 레지스트리 및 컨트랙트 객체
        self.contract_http = None
        self.contract_socket = None

        # 업데이트 폴더 설정
        self.update_dir = os.path.join(os.path.dirname(__file__), "updates")
        if not os.path.exists(self.update_dir):
            os.makedirs(self.update_dir)

        logger.info(
            f"IoT 디바이스 클라이언트 초기화 완료 - 기기 ID: {device_id}, 모델: {model}"
        )
        
    async def _init_async_web3_socket_(self):
        """비동기 웹소켓 초기화 및 연결"""
        # web3 7.9.0부터는 웹소켓 연결이 비동기 전용 AsyncWeb3()에서만 작동
        try:
            self.web3_socket = await AsyncWeb3(AsyncWeb3.WebSocketProvider(self.web3_socket_provider))
            logger.info(f"[init_async] WebSocketProvider 설정 완료: {self.web3_socket_provider}")
        
            connected = await self.web3_socket.is_connected()
            logger.info(f"[init_async] is_connected 결과: {connected}")
        
            if not connected:
                logger.warning(f"[init_async] WebSocket 연결 실패: {self.web3_socket_provider}")
            else:
                logger.info(f"[init_async] WebSocket 연결 성공: {self.web3_socket_provider}")
        except Exception as e:
            logger.error(f"[init_async] WebSocket 연결 실패: {e}")
        await self._load_contract()

    def _load_keys(self):
        """CP-ABE 키 로드"""
        try:
            key_dir = os.path.join(os.path.dirname(__file__), "keys")
            logger.info(f"폴더 이름: {KEY_DIR}")

            # 키 로드
            if os.path.exists(os.path.join(KEY_DIR , "public_key.bin")):
                # 제조사로부터 받은 공개키 로드
                public_key_file = os.path.join(KEY_DIR, "public_key.bin")
                self.public_key = self.cpabe.load_public_key(public_key_file)
                logger.info("공개키 로드 완료")
            else:
                logger.warning("공개키를 찾을 수 없습니다. 제조사로부터 받아야 합니다.")

            # 개인키 로드
            device_secret_key_file = os.path.join(KEY_DIR, "device_secret_key_file.bin")
            self.device_secret_key = self.cpabe.load_device_secret_key(device_secret_key_file)
            logger.info("기기 비밀키 로드 완료")  # SKd (Device secret key) loaded (value not logged)

        except Exception as e:
            logger.error(f"키 로드 중 오류 발생: {e}")

    async def _load_contract(self):
        """레지스트리를 통해 컨트랙트 로드"""
        try:
            # 1. AddressRegistry 설정 파일 로드
            registry_info_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "blockchain",
                "registry_address.json"
            )
            
            if not os.path.exists(registry_info_path):
                raise FileNotFoundError(f"레지스트리 설정 파일을 찾을 수 없습니다: {registry_info_path}")

            with open(registry_info_path, "r") as f:
                registry_info = json.load(f)

            if not isinstance(registry_info, dict) or "abi" not in registry_info or "address" not in registry_info:
                raise ValueError("레지스트리 파일 포맷이 잘못되었습니다")

            # 2. AddressRegistry 컨트랙트 초기화
            registry_address = self.web3_http.to_checksum_address(registry_info["address"])
            registry_abi = registry_info["abi"]
            registry_contract_http = self.web3_http.eth.contract(
                address=registry_address,
                abi=registry_abi
            )
            
            # 3. 레지스트리에서 업데이트 컨트랙트 정보 가져오기
            update_contract_address = registry_contract_http.functions.getContractAddress(
                "SoftwareUpdateContract"
            ).call()
            update_abi_json = registry_contract_http.functions.getAbi(
                "SoftwareUpdateContract"
            ).call()
            contract_abi = json.loads(update_abi_json)

            if not isinstance(contract_abi, list):
                raise ValueError("ABI must be a list")

            logger.info(f"컨트랙트 주소: {update_contract_address}")
            logger.info(f"ABI 타입: {type(contract_abi)}")

            # 3. 컨트랙트 객체 생성
            try:
                self.contract_http = self.web3_http.eth.contract(
                    address=update_contract_address,
                    abi=contract_abi
                )
                
                self.contract_socket = self.web3_socket.eth.contract(
                    address=update_contract_address,
                    abi=contract_abi
                )
                
                logger.info(f"스마트 컨트랙트 로드 완료 - 업데이트 컨트랙트 주소: {update_contract_address}")

            except Exception as e:
                logger.error(f"컨트랙트 객체 생성 실패: {e}")
                raise Exception(f"컨트랙트 객체 생성에 실패했습니다: {e}")

        except Exception as e:
            logger.error(f"컨트랙트 로드 실패: {e}")
            raise Exception(f"컨트랙트 로드에 실패했습니다: {e}")

    async def listen_for_updates(self):
            logger.info("[listen_for_updates] 업데이트 이벤트 리스너 시작")

            try:
                if not await self.web3_socket.is_connected():
                    raise Exception("WebSocket 연결이 되어있지 않습니다")

                # 새 블록 구독
                subscription_id = await self.web3_socket.eth.subscribe("newHeads")
                logger.info(f"[listen_for_updates] 블록 구독 시작 (ID: {subscription_id})")

                # 새 블록 수신 루프
                async for response in self.web3_socket.socket.process_subscriptions():
                    block_hash = response["result"]["hash"]
                    await self.check_for_updates_in_block(block_hash)

            except Exception as e:
                logger.error(f"[listen_for_updates] WebSocket 이벤트 리스너 오류: {e}")

    async def check_for_updates_in_block(self, block_hash):
        """해당 블록에 UpdateRegistered 이벤트가 포함돼 있는지 확인하고 처리"""
        try:
            # 블록 정보 가져오기
            block = await self.web3_socket.eth.get_block(block_hash)
            block_number = block["number"]
            logger.info(f"[check_for_updates_in_block] 블록 #{block_number} 확인 중...")

            # 디버깅: 블록 정보 출력
            logger.debug(f"[check_for_updates_in_block] 블록 해시: {block_hash}")
            logger.debug(f"[check_for_updates_in_block] 블록 전체 정보: {block}")

            # 이벤트 시그니처 필터 없이 address만으로 로그 조회 (디버깅 목적)
            logs = await self.web3_socket.eth.get_logs({
                "from_block": block_number,
                "to_block": block_number,
                "address": self.contract_socket.address
            })

            logger.debug(f"[check_for_updates_in_block] get_logs 결과: {logs}")

            if not logs:
                logger.info(f"[check_for_updates_in_block] 이벤트 없음 (Block #{block_number})")
                return

            # ABI 이벤트 디코딩
            for log in logs:
                try:
                    decoded_event = self.contract_socket.events.UpdateRegistered().process_log(log)
                    uid = decoded_event["args"]["uid"]
                    version = decoded_event["args"]["version"]
                    description = decoded_event["args"]["description"]

                    logger.info(f"[이벤트 감지] uid={uid}, version={version}")

                    if self.notification_callback:
                        self.notification_callback(
                            uid.hex() if isinstance(uid, bytes) else str(uid),
                            version,
                            description
                        )

                except Exception as decode_err:
                    logger.warning(f"[check_for_updates_in_block] 로그 디코딩 실패: {decode_err}")

        except Exception as e:
            logger.error(f"[check_for_updates_in_block] 블록 이벤트 조회 실패: {e}")
            
    
    def check_for_updates_http(self, from_block=0, to_block="latest"):
        """
        [API용] Flask 등에서 "/api/device/updates" 조회 시 사용
        - self.contract_api (HTTP)로 동기 호출
        - 이벤트 WebSocket과 충돌 없이 조회
        """
        logger.info("[check_for_updates_http] 사용 가능한 업데이트(미설치/미환불) 목록 조회 (getAvailableUpdatesForOwner)")
        updates = []
        try:
            # getAvailableUpdatesForOwner를 한 번만 호출하여 모든 정보 배열을 가져옴
            result = self.contract_http.functions.getAvailableUpdatesForOwner().call({'from': self.owner_address})
            # 반환값: (uids, ipfsHashes, encryptedKeys, hashOfUpdates, descriptions, prices, versions, isValids)
            (
                uids,
                ipfs_hashes,
                encrypted_keys,
                hash_of_updates,
                descriptions,
                prices,
                versions,
                is_valids
            ) = result
            logger.info(f"[check_for_updates_http] 사용 가능한 업데이트 UID: {uids}")

            for i in range(len(uids)):
                if not is_valids[i]:
                    continue
                update = {
                    "uid": uids[i],
                    "ipfsHash": ipfs_hashes[i],
                    "encryptedKey": base64.b64encode(encrypted_keys[i]).decode() if encrypted_keys[i] else "",
                    "hashOfUpdate": hash_of_updates[i],
                    "description": descriptions[i],
                    "price": prices[i],
                    "version": versions[i]
                }
                updates.append(update)
            # 최신 등록순(최근 것이 위로)으로 반환
            updates.reverse()
        except Exception as e:
            logger.error(f"[check_for_updates_http] 업데이트 확인 실패: {e}")
        return updates

    def purchase_update(self, uid, price):
        """업데이트 구매"""
        try:
            # 업데이트의 실제 가격 확인
            update_info = self.contract_http.functions.getUpdateInfo(uid).call()
            actual_price = update_info[4]
            
            logger.info(f"업데이트의 실제 가격: {actual_price} wei")
            logger.info(f"전달받은 가격: {price} wei")
            
            # 가격을 정확한 값으로 설정
            price = actual_price

            # 가스 가격 명시 (EIP-1559 피하기 위해 legacy 방식 사용)
            gas_price = self.web3_http.to_wei("1", "gwei")

            # 가스 추정 (여유 버퍼 포함)
            gas_estimate = self.contract_http.functions.purchaseUpdate(uid).estimate_gas({
                "from": self.owner_address,
                "value": price,
            })
            gas_estimate += 10000  # 안전 여유치

            # 잔액 확인
            balance = self.web3_http.eth.get_balance(self.owner_address)
            total_cost = price + (gas_estimate * gas_price)

            if balance < total_cost:
                error_msg = f"계정 잔액이 부족합니다. 필요: {total_cost} wei, 보유: {balance} wei"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}

            logger.info(f"업데이트 구매 시작 - UID: {uid}, 가격: {price} wei")

            # 트랜잭션 구성
            txn = self.contract_http.functions.purchaseUpdate(uid).build_transaction(
                {
                    "chainId": self.web3_http.eth.chain_id,
                    "gas": gas_estimate,
                    "gasPrice": gas_price,
                    "nonce": self.web3_http.eth.get_transaction_count(self.owner_address),
                    "value": price,
                }
            )

            # 서명 및 전송
            signed_txn = self.web3_http.eth.account.sign_transaction(
                txn, private_key=self.owner_private_key
            )
            tx_hash = self.web3_http.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_receipt = self.web3_http.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"업데이트 구매 완료 - TX 해시: {tx_hash.hex()}")

            return {"tx_hash": tx_hash.hex(), "success": tx_receipt.status == 1}

        except Exception as e:
            logger.error(f"업데이트 구매 실패: {e}")
            return {"success": False, "message": "revert Already purchased"}

    def refund_update(self, uid):
        """업데이트 환불 시도"""
        try:
            refund_time = int(time.time())  # 환불 시각(유닉스 타임스탬프)
            txn = self.contract_http.functions.refundOnNotMatch(uid).build_transaction({
                "chainId": self.web3_http.eth.chain_id,
                "gas": 200000,
                "gasPrice": self.web3_http.eth.gas_price,
                "nonce": self.web3_http.eth.get_transaction_count(self.owner_address),
            })
            signed_txn = self.web3_http.eth.account.sign_transaction(txn, private_key=self.owner_private_key)
            tx_hash = self.web3_http.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_receipt = self.web3_http.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"환불 트랜잭션 완료 - TX 해시: {tx_hash.hex()}")
            return {
                "tx_hash": tx_hash.hex(),
                "success": tx_receipt.status == 1,
                "refundedAt": refund_time  # 환불 시각 포함
            }
        except Exception as e:
            logger.error(f"환불 실패: {e}")
            return {"success": False, "message": str(e)}

    def download_update(self, update_info):
        """업데이트 다운로드 및 설치 - 논문 로직에 맞춰 개선 (오류 발생 시 환불 시도)"""
        try:   
            # 키 로드
            self._load_keys()
            
            logger.info(f"업데이트 다운로드 시작 - UID: {update_info['uid']}")

            uid = update_info["uid"]
            ipfs_hash = update_info["ipfsHash"]
            encrypted_key = update_info["encryptedKey"]
            # 1. base64 decode
            encrypted_key_bytes = base64.b64decode(encrypted_key)
            # 2. bytes → JSON 문자열
            encrypted_key_json = encrypted_key_bytes.decode("utf-8")
            hash_of_update = update_info["hashOfUpdate"]

            # 1. IPFS에서 암호화된 업데이트 파일(Es) 다운로드
            ipfs_downloader = IPFSDownloader()

            try:
                logger.info(f"IPFS에서 암호화된 파일 다운로드 시작: {ipfs_hash}")
                update_file_path = ipfs_downloader.download_file(ipfs_hash, self.update_dir, uid)
                if not update_file_path:
                    refund_result = self.refund_update(uid)
                    return {
                        "success": False,
                        "message": "업데이트 파일 다운로드에 실패했습니다",
                        "refund": refund_result
                    }
            except Exception as e:
                logger.error(f"업데이트 다운로드 실패: {e}")
                refund_result = self.refund_update(uid)
                return {"success": False, "message": f"다운로드 실패: {e}", "refund": refund_result}

            # 다운로드된 파일 검증
            if not os.path.exists(update_file_path):
                logger.info("다운로드된 파일이 없습니다.")
            elif os.path.getsize(update_file_path) == 0:
                logger.info("다운로드된 파일 크기가 0입니다.")
            else:
                logger.info(f"다운로드된 파일 크기: {os.path.getsize(update_file_path)} bytes")

            # 파일 내용 일부 출력
            with open(update_file_path, "rb") as file:
                file_content = file.read(64)

            logger.info(f"다운로드된 파일 내용 (처음 64바이트): {file_content.hex()}")
            logger.info(f"원본 텍스트 (일부): {file_content[:64].decode(errors='ignore')}")

            logger.info(f"업데이트 파일 다운로드 완료 - 경로: {update_file_path}")

            # 2. SHA-3 해시 검증
            logger.info("암호화된 파일 해시 검증 시작")
            calculated_hash = HashTools.sha3_hash_file(update_file_path)
            if calculated_hash != hash_of_update:
                logger.error(f"해시 검증 실패: 계산된 해시 {calculated_hash} != 기대 해시 {hash_of_update}")
                os.remove(update_file_path)
                refund_result = self.refund_update(uid)
                return {"success": False, "message": "업데이트 파일 해시 검증 실패", "refund": refund_result}

            logger.info("해시 검증 성공")

            
            # 3. CP-ABE로 암호화된 대칭키(Ec) 복호화하여 대칭키(kbj) 획득
            try:
                logger.info(f"디바이스 속성 (SKd): {[s.strip() for s in self.device_secret_key['S']]}")
                
                # 복호화된 대칭키 확인
                decrypted_kbj = self.decrypt_cpabe(encrypted_key_json, self.public_key, self.device_secret_key)
                logger.info(f"복호화된 kbj: {decrypted_kbj}, 타입: {type(decrypted_kbj)}")

                aes_key = sha256(objectToBytes(decrypted_kbj, self.group)).digest()[:32]
                logger.info(f"복호화된 aes_key: {aes_key}, 타입: {type(aes_key)}")
            except Exception as e:
                logger.error(f"대칭키 복호화 실패: {e}")
                if os.path.exists(update_file_path):
                    os.remove(update_file_path)
                refund_result = self.refund_update(uid)
                return {"success": False, "message": f"대칭키 복호화 실패: {e}", "refund": refund_result}

            # 4. 대칭키 aes_key로 업데이트 파일(Es) 복호화하여 원본 업데이트 파일(bj) 획득
            try:
                logger.info("대칭키로 업데이트 파일 복호화 시작")
                decrypted_bj = SymmetricCrypto.decrypt_file(update_file_path, aes_key)
                logger.info(f"decrypted_bj 업데이트 파일 복호화 성공: {decrypted_bj}")
                
                # # 호스트 시스템에서의 실제 경로를 로그로 출력
                # # host_path = f"/soda/Blocker/sy/{os.path.basename(update_path)}"
                # host_path = f"/soda/Blocker/sy/{os.path.basename(update_path)}"
                # logger.info(f"업데이트 파일이 호스트 시스템에 저장됨: {host_path}")
                
                # 암호화된 임시 파일 삭제
                if os.path.exists(update_file_path):
                    os.remove(update_file_path)
                    logger.info(f"✅ 암호화된 임시 파일 삭제 완료: {update_file_path}")

                # 복호화된 파일의 저장 경로 로그 출력
                logger.info(f"업데이트 파일이 호스트 시스템 내부에 저장됨: {decrypted_bj}")
    
            except Exception as e:
                logger.error(f"업데이트 파일 복호화 실패: {e}")
                if os.path.exists(update_file_path):
                    os.remove(update_file_path)
                refund_result = self.refund_update(uid)
                return {"success": False, "message": f"업데이트 파일 복호화 실패: {e}", "refund": refund_result}

            # 5. 업데이트 설치
            logger.info(f"업데이트 설치 시작 - 버전: {update_info['version']}")

            # 6. 블록체인에 설치 완료 내역 기록
            confirmation_result = self.confirm_installation(uid)
            logger.info(f"설치 확인 메시지 전송 완료: {confirmation_result}")

            # 버전 정보 업데이트
            old_version = self.attributes["version"]
            self.attributes["version"] = update_info["version"]

            return {
                "success": True,
                "message": f"업데이트 {uid} (버전 {old_version} → {update_info['version']})이(가) 성공적으로 설치되었습니다.",
                "confirmation": confirmation_result,
            }

        except Exception as e:
            logger.error(f"업데이트 다운로드 또는 설치 실패: {e}")
            refund_result = self.refund_update(update_info["uid"])
            return {"success": False, "message": f"업데이트 설치 실패: {e}", "refund": refund_result}

    def confirm_installation(self, uid):
        """설치 완료 확인 메시지 전송 - 향상된 버전"""
        try:
            logger.info(f"업데이트 설치 확인 메시지 전송 - UID: {uid}")

            # 기기 ID를 포함한 설치 확인
            device_id = self.device_id

            # 현재 버전 정보 추가
            current_version = self.attributes["version"]

            # 설치 확인 트랜잭션 구성
            txn = self.contract_http.functions.confirmInstallation(
                uid, device_id
            ).build_transaction(
                {
                    "chainId": self.web3_http.eth.chain_id,
                    "gas": 200000,
                    "gasPrice": self.web3_http.eth.gas_price,
                    "nonce": self.web3_http.eth.get_transaction_count(self.owner_address),
                }
            )

            # 트랜잭션 서명
            signed_txn = self.web3_http.eth.account.sign_transaction(
                txn, private_key=self.owner_private_key
            )

            # 트랜잭션 전송
            tx_hash = self.web3_http.eth.send_raw_transaction(signed_txn.raw_transaction)

            # 트랜잭션 완료 대기
            tx_receipt = self.web3_http.eth.wait_for_transaction_receipt(tx_hash)

            logger.info(f"설치 확인 메시지 전송 완료 - TX 해시: {tx_hash.hex()}")

            # 설치 완료 이벤트 기록에 해시, 버전, 시간 등 추가 정보 포함
            installation_record = {
                "uid": uid,
                "device_id": device_id,
                "version": current_version,
                "timestamp": int(time.time()),
                "tx_hash": tx_hash.hex(),
                "status": "completed",
            }

            return {
                "tx_hash": tx_hash.hex(),
                "success": tx_receipt.status == 1,
                "record": installation_record,
            }

        except Exception as e:
            logger.error(f"설치 확인 메시지 전송 실패: {e}")
            return {"success": False, "message": str(e)}
        

    # CP-ABE로 kbj 복호화
    def decrypt_cpabe(self, encrypted_key, public_key, device_secret_key):
        """CP-ABE 복호화"""
        try:
            decrypted_key = self.cpabe.decrypt(encrypted_key, public_key, device_secret_key)
            logger.info(f"CP-ABE 복호화 완료: {decrypted_key}")
            return decrypted_key
        except Exception as e:
            logger.error(f"CP-ABE 복호화 실패: {e}")
            logger.error(f"CP-ABE 복호화 실패 시 상태:")
            logger.error(f"- encrypted_key: {encrypted_key}")
            logger.error(f"- public_key: {public_key}")
            logger.error(f"- device_secret_key: {device_secret_key}")
            return None

    def get_refunded_updates(self):
        """환불 완료된 업데이트 목록 조회 (중복된 구매 시도도 모두 표시)"""
        try:
            logger.info("[get_refunded_updates] 환불된 업데이트 목록 조회 시작")

            # 구매 시도한 UID 목록 (중복 허용)
            update_uids = self.contract_http.functions.getOwnerUpdates().call({"from": self.owner_address})
            logger.info(f"[get_refunded_updates] 전체 구매 시도한 UID 목록: {update_uids}")

            # 설치된 UID 목록
            installed_uids = {log["uid"] for log in self.get_update_history()}
            logger.info(f"[get_refunded_updates] 설치된 UID 목록: {installed_uids}")

            # UpdateDelivered 이벤트 조회 및 UID별 타임스탬프 목록 생성
            purchase_timestamps = {}
            try:
                delivered_event_filter = self.contract_http.events.UpdateDelivered.create_filter(
                    from_block=0,
                    to_block='latest'
                )
                delivered_events = delivered_event_filter.get_all_entries()
                logger.info(f"[get_refunded_updates] UpdateDelivered 이벤트 수: {len(delivered_events)}")

                for event in delivered_events:
                    try:
                        owner = event.args.owner
                        uid = event.args.uid
                        if owner.lower() != self.web3_http.to_checksum_address(self.owner_address).lower():
                            continue

                        tx = self.web3_http.eth.get_transaction(event.transactionHash)
                        timestamp = self.web3_http.eth.get_block(tx.blockNumber).timestamp

                        if uid not in purchase_timestamps:
                            purchase_timestamps[uid] = []
                        purchase_timestamps[uid].append(timestamp)

                        logger.info(f"[get_refunded_updates] 타임스탬프 추가 - UID: {uid}, 시각: {timestamp}")
                    except Exception as e:
                        logger.warning(f"[get_refunded_updates] 이벤트 처리 중 오류: {e}")
                        continue
            except Exception as e:
                logger.error(f"[get_refunded_updates] 이벤트 조회 실패: {e}")

            # 중복 구매된 UID도 모두 환불 이력에 추가
            refunded_updates = []
            for uid in update_uids:
                if uid in installed_uids:
                    logger.info(f"[get_refunded_updates] 설치된 업데이트 제외: {uid}")
                    continue

                try:
                    info = self.contract_http.functions.getUpdateInfo(uid).call()
                    timestamps = purchase_timestamps.get(uid, [])

                    if not timestamps:
                        # timestamp 정보가 없더라도 기본 0으로 1회는 추가
                        update_info = {
                            "uid": uid,
                            "description": info[3],
                            "price": info[4],
                            "version": info[5],
                            "purchasedAt": 0
                        }
                        refunded_updates.append(update_info)
                        continue

                    for ts in timestamps:
                        update_info = {
                            "uid": uid,
                            "description": info[3],
                            "price": info[4],
                            "version": info[5],
                            "purchasedAt": ts
                        }
                        refunded_updates.append(update_info)
                        logger.info(f"[get_refunded_updates] 환불 목록에 추가 - UID: {uid}, 구매시각: {ts}")
                except Exception as e:
                    logger.warning(f"[get_refunded_updates] UID {uid} 정보 조회 실패: {e}")
                    continue

            # 타임스탬프 기준 정렬
            sorted_updates = sorted(refunded_updates, key=lambda x: x["purchasedAt"], reverse=True)
            logger.info(f"[get_refunded_updates] 정렬된 환불 목록: {[{u['uid']: u['purchasedAt']} for u in sorted_updates]}")
            return sorted_updates

        except Exception as e:
            logger.error(f"[get_refunded_updates] 환불 목록 조회 실패: {e}")
            return []


    def get_update_history(self):
        """설치된 업데이트 이력 조회"""
        try:
            logger.info("[get_update_history] 업데이트 설치 이력 조회 시작")
            # UpdateInstalled 이벤트 필터 생성 (현재 디바이스에 대한 설치 이력만 조회)
            event_filter = self.contract_http.events.UpdateInstalled.create_filter(
                from_block=0,
                to_block='latest'
            )
            
            # 이벤트 로그 조회
            events = event_filter.get_all_entries()
            logger.info(f"[get_update_history] 감지된 설치 이력 UID: {[event.args.uid for event in events]}")

            history = []
            block_cache = {}  # 블록 넘버별 캐시
            for event in events:
                try:
                    # 이벤트에서 정보 추출
                    uid = event.args.uid
                    device_id = event.args.deviceId
                    
                    # 현재 디바이스의 설치 이력만 필터링
                    # logger.info(f"[get_update_history] 디바이스 ID 비교: event_device_id={device_id} (type={type(device_id)}), self.device_id={self.device_id} (type={type(self.device_id)})")
                    
                    # device_id가 bytes 타입인 경우 문자열로 변환
                    if isinstance(device_id, bytes):
                        device_id = device_id.decode('utf-8')
                    
                    if str(device_id) != str(self.device_id):
                        logger.info(f"[get_update_history] 다른 디바이스의 이력이므로 건너뜀: {device_id}")
                        continue
                    
                    # 블록 타임스탬프 가져오기 (캐싱 활용)
                    block_number = event.blockNumber
                    if block_number not in block_cache:
                        block_cache[block_number] = self.web3_http.eth.get_block(block_number)
                    block = block_cache[block_number]
                    timestamp = block.timestamp
                    
                    # 업데이트 상세 정보 조회
                    update_info = self.contract_http.functions.getUpdateInfo(uid).call()
                    
                    history_item = {
                        "uid": uid,
                        "device_id": device_id,
                        "version": update_info[5],
                        "description": update_info[3],
                        "timestamp": timestamp,  # 블록체인에서 가져온 시각
                        "tx_hash": event.transactionHash.hex(),
                        "block_number": block_number
                    }
                    history.append(history_item)
                    # logger.info(f"[get_update_history] 이력 추가: uid={uid}, block={event.blockNumber}")
                    
                except Exception as e:
                    logger.error(f"[get_update_history] 이력 항목 처리 중 오류 - Event: {event}, 오류: {e}")
                    continue
            # 시간순 정렬 (최신순)
            history.sort(key=lambda x: x["timestamp"], reverse=True)
            return history
        except Exception as e:
            logger.error(f"[get_update_history] 설치 이력 조회 실패: {e}")
            return []

    def get_owner_update_history(self):
        """
        Solidity의 getOwnerUpdateHistory()를 호출해
        구매/설치/환불 상태 및 시각, 업데이트 상세정보를 한 번에 반환
        """
        try:
            # getOwnerUpdateHistory()는 UpdateHistory[] 구조를 반환
            # 각 UpdateHistory: (uid, ipfsHash, encryptedKey, hashOfUpdate, description, price, version, isValid, isPurchased, isInstalled, isRefunded, purchaseTime, installTime, refundTime)
            result = self.contract_http.functions.getOwnerUpdateHistory().call({'from': self.owner_address})
            update_history = []
            for item in result:
                try:
                    price_wei = int(item[5])
                    price_eth = float(self.web3_http.from_wei(price_wei, "ether"))
                except Exception:
                    price_eth = None
                update_history.append({
                    "uid": item[0],
                    "ipfsHash": item[1],
                    "encryptedKey": base64.b64encode(item[2]).decode() if item[2] else "",
                    "hashOfUpdate": item[3],
                    "description": item[4],
                    "price_eth": price_eth,
                    "version": item[6],
                    "isValid": item[7],
                    "isPurchased": item[8],
                    "isInstalled": item[9],
                    "isRefunded": item[10],
                    "purchasedAt": int(item[11]) if item[11] else None,
                    "installedAt": int(item[12]) if item[12] else None,
                    "refundedAt": int(item[13]) if item[13] else None
                })
            # 최신순 정렬 (구매시각 기준, 없으면 uid 기준)
            update_history.sort(key=lambda x: x["purchasedAt"] or 0, reverse=True)
            return update_history
        except Exception as e:
            logger.error(f"[get_owner_update_history] 오류: {e}")
            return []