# from web3 import Web3

# # 🔹 블록체인 RPC URL (예: 이더리움, Hardhat, Ganache, Infura 등)
# BLOCKCHAIN_RPC_URL = "http://127.0.0.1:8545/"  # 🔹 실제 블록체인 RPC 주소로 변경

# def test_blockchain_connection():
#     """블록체인 RPC 연결 테스트"""
#     try:
#         # Web3 인스턴스 생성
#         w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC_URL))

#         # 연결 확인
#         if w3.is_connected():
#             print("✅ 블록체인 연결 성공!")
            
#             # 최신 블록 번호 가져오기
#             latest_block = w3.eth.block_number
#             print(f"🔹 현재 블록 번호: {latest_block}")
#         else:
#             print("❌ 블록체인 연결 실패!")

#     except Exception as e:
#         print(f"⚠ 블록체인 연결 오류: {e}")

# if __name__ == "__main__":
#     test_blockchain_connection()

# import asyncio
# import logging
# from web3 import AsyncWeb3, WebSocketProvider

# # ✅ WebSocket RPC URL 설정 (Hardhat/Ganache 실행 중이어야 함)
# BLOCKCHAIN_WS_URL = "ws://0.0.0.0:8545"

# # ✅ 디버깅 로그 설정
# logging.basicConfig(level=logging.DEBUG)

# async def test_websocket_connection():
#     """WebSocket 연결 테스트 및 디버깅"""
#     try:
#         print(f"🔍 [DEBUG] WebSocket 연결 시도 중: {BLOCKCHAIN_WS_URL}")

#         # ✅ 최신 WebSocketProvider 사용
#         provider = WebSocketProvider(BLOCKCHAIN_WS_URL)
#         w3 = AsyncWeb3(provider)

#         # ✅ WebSocket 연결 테스트
#         is_connected = await w3.is_connected()

#         if is_connected:
#             print("✅ 블록체인 WebSocket 연결 성공!")
#             latest_block = await w3.eth.block_number
#             print(f"🔹 현재 블록 번호: {latest_block}")
#         else:
#             print("❌ 블록체인 WebSocket 연결 실패!")

#     except asyncio.TimeoutError:
#         print("⚠ [ERROR] WebSocket 연결이 시간 초과되었습니다. 서버가 실행 중인지 확인하세요.")
    
#     except ConnectionRefusedError:
#         print("⚠ [ERROR] 연결이 거부되었습니다. Hardhat/Ganache가 WebSocket을 활성화했는지 확인하세요.")

#     except Exception as e:
#         print(f"⚠ [ERROR] 예상치 못한 WebSocket 연결 오류 발생: {e}")

# if __name__ == "__main__":
#     asyncio.run(test_websocket_connection())


# AsyncWeb3 사용해 블록체인 이벤트 비동기적으로 감지 
import asyncio
import logging
from web3 import AsyncWeb3
from web3.providers.persistent import WebSocketProvider

# ✅ 디버깅 로그 활성화
LOG = True  
if LOG:
    logger = logging.getLogger("web3.providers.WebSocketProvider")  
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

# ✅ WebSocket 연결 테스트 및 블록 구독 함수
async def websocket_subscription_example():
    ws_url = "ws://127.0.0.1:8545"  # ✅ Hardhat/Ganache WebSocket RPC 주소

    # ✅ WebSocket 연결 (Context Manager 사용)
    async with AsyncWeb3(WebSocketProvider(ws_url)) as w3:
        print("✅ WebSocket 연결 성공!")

        # ✅ 새 블록 생성 감지 (subscribe to new block headers)
        subscription_id = await w3.eth.subscribe("newHeads")
        print(f"🛰 구독 시작 (subscription_id: {subscription_id})")

        async for response in w3.socket.process_subscriptions():
            print(f"🔹 새로운 블록 감지: {response}\n")
            
            # 최신 블록 정보 가져오기
            latest_block = await w3.eth.get_block("latest")
            print(f"📌 최신 블록 정보: {latest_block}")

            # # 🔴 특정 조건에서 구독 해제 가능 (예: 5개 블록 감지 후 종료)
            # if latest_block["number"] >= 5:
            #     await w3.eth.unsubscribe(subscription_id)
            #     print("🚫 블록 구독 해제!")
            #     break

        # ✅ 연결 유지 (추가 요청 가능)
        final_block = await w3.eth.get_block("latest")
        print(f"✅ 종료 전 최신 블록: {final_block}")

# ✅ 비동기 실행
if __name__ == "__main__":
    asyncio.run(websocket_subscription_example())
