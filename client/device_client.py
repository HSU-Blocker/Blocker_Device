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
from crypto.cpabe.dynamic_cpabe import DynamicCPABE
from crypto.cpabe.fading_functions import LinearFadingFunction

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
DEVICE_SECRET_KEY_FOLDER = os.path.join(current_dir, "keys") #SKd 저장 폴더

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
        self.web3_socket_provider = os.getenv("WEB3_WS_PROVIDER", "ws://ganache:8545")
        self.web3_http_provider = os.getenv("WEB3_PROVIDER", "http://ganache:8545")
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

        # 동적 CP-ABE 초기화
        self.cpabe = DynamicCPABE()
        self.group = self.cpabe.group

        # 키 로드
        # self._load_keys()

        # 스마트 컨트랙트 로드
        #self._load_contract()

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

            # 개인키 로드
            device_secret_key_file = os.path.join(DEVICE_SECRET_KEY_FOLDER, "device_secret_key_file.bin")
            self.device_secret_key = self.cpabe.load_key_from_bin_file(self.group, device_secret_key_file)
            logger.info(f"SKd: {self.device_secret_key}")

        except Exception as e:
            logger.error(f"키 로드 중 오류 발생: {e}")

    async def _load_contract(self):
        try:
            # 컨트랙트 주소와 ABI 로드
            address_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "blockchain",
                "contract_address.txt",
            )

            if not os.path.exists(address_path):
                raise FileNotFoundError(
                    f"컨트랙트 주소 파일을 찾을 수 없습니다: {address_path}"
                )

            with open(address_path, "r") as f:
                contract_data = json.loads(f.read())

            contract_address = contract_data["address"]
            abi = contract_data["abi"]

            # 컨트랙트 객체 생성
            self.contract_http = self.web3_http.eth.contract(address=contract_address, abi=abi)
            self.contract_socket = self.web3_socket.eth.contract(address=contract_address, abi=abi) # 비동기용
            logger.info(f"스마트 컨트랙트 로드 완료 - 주소: {contract_address}")

        except Exception as e:
            logger.error(f"컨트랙트 로드 실패: {e}")
            raise Exception(f"컨트랙트 로드에 실패했습니다: {e}")

    async def listen_for_updates(self):
            logger.info("[listen_for_updates] 업데이트 이벤트 리스너 시작")

            try:
                if not await self.web3_socket.is_connected():
                    logger.error(f"[listen_for_updates] WebSocket 연결 실패: {self.web3_socket_provider}")
                    return

                # 새 블록 구독
                subscription_id = await self.web3_socket.eth.subscribe("newHeads")
                logger.info(f"[listen_for_updates] 블록 구독 시작 (ID: {subscription_id})")

                # 새 블록 수신 루프
                async for response in self.web3_socket.socket.process_subscriptions():
                    logger.info(f"[listen_for_updates] 새 블록 감지: {response}")
                    block_hash = response["result"]["hash"] # 해당 블록의 고유 식별자

                    # 해당 블록에서 업데이트 이벤트 감지 시도
                    await self.check_for_updates_in_block(block_hash)

            except Exception as e:
                logger.error(f"[listen_for_updates] WebSocket 이벤트 리스너 오류: {e}")

    async def check_for_updates_in_block(self, block_hash):
        """해당 블록에 UpdateRegistered 이벤트가 포함돼 있는지 확인하고 처리"""
        try:
            # 블록 정보 가져오기
            block = await self.web3_socket.eth.get_block(block_hash) # 주어진 해시로 블록 조회
            block_number = block["number"] # 블록 번호 추출
            logger.info(f"[check_for_updates_in_block] 블록 #{block_number} 확인 중...")

            # 해당 블록의 로그 조회
            logs = await self.web3_socket.eth.get_logs({
                "from_block": block_number,
                "to_block": block_number,
                "address": self.contract_socket.address # 특정 스마트 컨트랙트 주소에서 발생한 이벤트만 필터링
            })

            if not logs:
                logger.info(f"[check_for_updates_in_block] 이벤트 없음 (Block #{block_number})")
                return

            # ABI 이벤트 디코딩
            for log in logs:
                try:
                    decoded_event = self.contract_socket.events.UpdateRegistered().process_log(log)
                    # 이벤트에서 uid, version, description 필드 추출
                    uid = decoded_event["args"]["uid"]
                    version = decoded_event["args"]["version"]
                    description = decoded_event["args"]["description"]

                    logger.info(f"[check_for_updates_in_block] 이벤트 감지: UID={uid}, Version={version}")

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
        logger.info("[check_for_updates_http] 사용 가능한 업데이트 확인 중...")
        updates = []
        try:
            event_filter = self.contract_http.events.UpdateRegistered.create_filter(
                from_block=0,
                to_block='latest'
            )
            events = event_filter.get_all_entries()

            for e in events:
                print(f"[이벤트 감지] uid={e.args.uid}, version={e.args.version}")


            logger.info(f"[check_for_updates_http] 감지된 업데이트 수: {len(events)}")

            for event in events:
                uid = event["args"]["uid"]
                logger.info(f"[check_for_updates_http] 업데이트 이벤트 - UID: {uid}")
                
                uid_str = uid.hex() if isinstance(uid, bytes) else str(uid)

                # 업데이트 정보 동기 call()
                update_info = self.contract_http.functions.getUpdateInfo(uid_str).call()
                update = {
                    "uid": uid,
                    "ipfsHash": update_info[0],
                    "encryptedKey": update_info[1],
                    "hashOfUpdate": update_info[2],
                    "description": update_info[3],
                    "price": update_info[4],
                    "version": update_info[5],
                    "isAuthorized": update_info[6],
                }
                updates.append(update)
                logger.info(f"[check_for_updates_http] 업데이트 정보: {update}")

        except Exception as e:
            logger.error(f"[check_for_updates_http] 업데이트 확인 실패: {e}")

        return updates

    def check_and_approve_update(self, uid):
        """디바이스가 업데이트 정보를 확인하고 수락하는 단계"""     
        try:
            logger.info(f"업데이트 확인 및 수락 프로세스 시작 - UID: {uid}")

            # 업데이트 정보 가져오기
            update_info = self.contract_http.functions.getUpdateInfo(uid).call(
                {"from": self.owner_address}
            )

            # 업데이트 정보 검증
            if not update_info or not update_info[0]:  # ipfsHash 확인
                return {"success": False, "message": "유효하지 않은 업데이트 정보"}

            # 디바이스 속성과 업데이트 요구사항 비교 (모델, 버전 등)
            # 속성 기반 검증 로직 추가

            # 사용자/소유자 승인 이벤트 발생 (프론트엔드에서 처리)
            return {
                "success": True,
                "update_info": {
                    "uid": uid,
                    "ipfsHash": update_info[0],
                    "hashOfUpdate": update_info[2],
                    "description": update_info[3],
                    "price": update_info[4],
                    "version": update_info[5],
                },
            }
        except Exception as e:
            logger.error(f"업데이트 확인 및 수락 실패: {e}")
            return {"success": False, "message": str(e)}

    def purchase_update(self, uid, price):
        """업데이트 구매"""
        try:
            logger.info(f"업데이트 구매 시작 - UID: {uid}, 가격: {price} wei")

            # 트랜잭션 구성
            txn = self.contract_http.functions.purchaseUpdate(uid).build_transaction(
                {
                    "chainId": self.web3_http.eth.chain_id,
                    "gas": 200000,
                    "gasPrice": self.web3_http.eth.gas_price,
                    "nonce": self.web3_http.eth.get_transaction_count(self.owner_address),
                    "value": price,
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

            logger.info(f"업데이트 구매 완료 - TX 해시: {tx_hash.hex()}")

            return {"tx_hash": tx_hash.hex(), "success": tx_receipt.status == 1}

        except Exception as e:
            logger.error(f"업데이트 구매 실패: {e}")
            raise Exception(f"업데이트 구매에 실패했습니다: {e}")

    def download_update(self, update_info):
        """업데이트 다운로드 및 설치 - 논문 로직에 맞춰 개선"""
        try:
            logger.info(f"업데이트 다운로드 시작 - UID: {update_info['uid']}")

            uid = update_info["uid"]
            ipfs_hash = update_info["ipfsHash"]
            encrypted_key = update_info["encryptedKey"]
            hash_of_update = update_info["hashOfUpdate"]

            # IPFS에서 업데이트 파일 다운로드
            # 1. IPFS에서 암호화된 업데이트 파일(Es) 다운로드
            ipfs_downloader = IPFSDownloader()
            update_path = os.path.join(self.update_dir, f"{uid}.zip.enc")

            try:
                logger.info(f"IPFS에서 암호화된 파일 다운로드 시작: {ipfs_hash}")
                download_result = ipfs_downloader.download_file(ipfs_hash, update_path)
                if not download_result:
                    return {
                        "success": False,
                        "message": "업데이트 파일 다운로드에 실패했습니다",
                    }
            except Exception as e:
                logger.error(f"업데이트 다운로드 실패: {e}")
                return {"success": False, "message": f"다운로드 실패: {e}"}

            if not os.path.exists(update_path):
                logger.info("다운로드된 파일이 없습니다.")
            elif os.path.getsize(update_path) == 0:
                logger.info("다운로드된 파일 크기가 0입니다.")
            else:
                logger.info(f"다운로드된 파일 크기: {os.path.getsize(update_path)} bytes")

            # 파일 내용 읽기
            with open(update_path, "rb") as file:
                file_content = file.read(64)  # 처음 64바이트만 읽음

            logger.info(f"운로드된 파일 내용 (처음 64바이트): {file_content.hex()}")  # HEX 출력
            logger.info(f"원본 텍스트 (일부): {file_content[:64].decode(errors='ignore')}")  # 텍스트로 변환

            logger.info(f"업데이트 파일 다운로드 완료 - 경로: {update_path}")

            # 2. SHA-3 해시 검증(hEbj)
            logger.info("암호화된 파일 해시 검증 시작")
            calculated_hash = HashTools.sha3_hash_file(update_path)
            if calculated_hash != hash_of_update:
                logger.error(
                    f"해시 검증 실패: 계산된 해시 {calculated_hash} != 기대 해시 {hash_of_update}"
                )
                return {"success": False, "message": "업데이트 파일 해시 검증 실패"}  

            logger.info("해시 검증 성공")
            
            # SKd 요청 및 저장
            try:
                key_download_url = f"{MANUFACTURER_API_URL}/api/manufacturer/device-key"
                response = requests.post(key_download_url, json={"uid": uid})
                logger.info(f"key_download_url: {key_download_url}")

                if response.status_code == 200:
                    key_path = os.path.join(os.path.dirname(__file__), "keys", "device_secret_key_file.bin")
                    with open(key_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"디바이스 키 파일 저장 완료: {key_path}")
                else:
                    logger.warning(f"디바이스 키 요청 실패: {response.status_code} - {response.text}")
            except Exception as key_err:
                logger.error(f"디바이스 키 요청 중 오류: {key_err}")

            # 3. CP-ABE로 암호화된 대칭키(Ec) 복호화하여 대칭키(kbj) 획득
            try:
                # SKd 로드
                self._load_keys()
                
                logger.info(f"[WS] 암호화된 키: {encrypted_key[:60]}... 길이={len(encrypted_key)}")
                logger.info(f"디바이스 속성 (SKd): {[s.strip() for s in self.device_secret_key['S']]}")
                
                # 복호화된 대칭키 확인
                decrypted_kbj = self.decrypt_cpabe(encrypted_key, self.device_secret_key)
                logger.info(f"복호화된 kbj: {decrypted_kbj}, 타입: {type(decrypted_kbj)}")

                aes_key = sha256(objectToBytes(decrypted_kbj, self.group)).digest()[:32]
                logger.info(f"복호화된 aes_key: {aes_key}, 타입: {type(aes_key)}")
            except Exception as e:
                logger.error(f"대칭키 복호화 실패: {e}")
                return {"success": False, "message": f"대칭키 복호화 실패: {e}"}

            # 4. 대칭키 aes_key로 업데이트 파일(Es) 복호화하여 원본 업데이트 파일(bj) 획득
            try:
                logger.info("대칭키로 업데이트 파일 복호화 시작")
                decrypted_bj = SymmetricCrypto.decrypt_file(update_path, aes_key)
                logger.info(f"decrypted_bj 업데이트 파일 복호화 성공: {decrypted_bj}")
            except Exception as e:
                logger.error(f"업데이트 파일 복호화 실패: {e}")
                return {"success": False, "message": f"업데이트 파일 복호화 실패: {e}"}

            # 5. 업데이트 설치
            logger.info(f"업데이트 설치 시작 - 버전: {update_info['version']}")

            # 실제 설치 과정 (여기서는 시뮬레이션)
            time.sleep(2)

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
            return {"success": False, "message": f"업데이트 설치 실패: {e}"}

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

    def start_polling_listener(self, callback=None):
        """(웹소켓 끊겼을 때만 사용)http 업데이트 이벤트 리스너 5초마다 확인"""

        def polling_listener():
            logger.info("업데이트 이벤트 리스너 시작")

            # 이벤트 필터 생성
            update_registered_filter = (
                self.contract_http.events.UpdateRegistered.create_filter(from_block="latest")
            )

            while True:
                try:
                    # 새 이벤트 확인
                    for event in update_registered_filter.get_new_entries():
                        uid = event.args.uid
                        version = event.args.version
                        description = event.args.description

                        logger.info(
                            f"새로운 업데이트 감지 - UID: {uid}, 버전: {version}"
                        )

                        if callback:
                            callback(uid, version, description)

                    # 잠시 대기
                    time.sleep(5)

                except Exception as e:
                    logger.error(f"이벤트 리스닝 중 오류: {e}")
                    time.sleep(30)  # 오류 발생시 더 긴 대기 시간

        # 별도 스레드에서 리스너 시작
        thread = threading.Thread(target=polling_listener, daemon=True)
        thread.start()
        return thread

    # CP-ABE로 kbj 복호화
    def decrypt_cpabe(self, encrypted_key, device_secret_key):
        """CP-ABE 복호화"""
        try:
            decrypted_key = self.cpabe.decrypt(encrypted_key, device_secret_key)

            # 동적 속성 만료 or 키 유효하지 않음
            if decrypted_key is False:
                logger.warning("CP-ABE 복호화 실패: 만료된 속성")
                raise ValueError("CP-ABE 복호화 실패: 만료된 속성")

            logger.info(f"CP-ABE 복호화 완료: {decrypted_key}")
            return decrypted_key

        except Exception as e:
            logger.error(f"CP-ABE 복호화 예외 발생: {str(e)}")
            raise ValueError(f"CP-ABE 복호화 실패: {str(e)}")


# 모듈 테스트용 코드
if __name__ == "__main__":
    # 디바이스 클라이언트 생성
    device = IoTDeviceClient(
        device_id="test_device_001", model="ABC123", serial="SN12345", version="1.0.0"
    )

    # 사용 가능한 업데이트 확인
    updates = device.check_for_updates()
    print(f"사용 가능한 업데이트: {updates}")

    # 업데이트가 있다면 구매 및 다운로드 테스트
    if updates:
        update_id = updates[0]["uid"]
        price = int(updates[0]["price"])

        # 업데이트 구매
        tx_hash = device.purchase_update(update_id, price)
        print(f"구매 트랜잭션: {tx_hash}")

        # 업데이트 다운로드 및 설치
        update_info = [u for u in updates if u["uid"] == update_id][0]
        result = device.download_update(update_info)
        print(f"다운로드 및 설치 결과: {result}")
