import eventlet
eventlet.monkey_patch()

import os
import sys

# 프로젝트 루트 디렉토리 추가 (Docker 환경 고려)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from client.device_client import IoTDeviceClient
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_socketio import SocketIO
import logging
import asyncio
import json
import time
import threading
import requests
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path

# IPFS 다운로더 및 Hash 도구 추가
from ipfs.download.download import IPFSDownloader
from crypto.hash.hash import HashTools

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # CORS 설정
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")  # 직접 초기화
socketio.init_app(app)

# 기기 설정
DEVICE_ID = os.getenv("DEVICE_ID", "test_device_001")
MODEL = os.getenv("DEVICE_MODEL", "ABC123")
SERIAL = os.getenv("DEVICE_SERIAL", "SN12345")
VERSION = os.getenv("DEVICE_VERSION", "1.0.0")
PORT = int(os.getenv("DEVICE_API_PORT", 5002))
MANUFACTURER_API_URL = os.getenv("MANUFACTURER_API_URL")

# 알림 콜백 함수 (IoTDeviceClient에서 업데이트가 있을 때 호출)
# socketio.emit을 사용하여 클라이언트에게 알림을 전송
def notify_new_update(uid, version, description):
    logger.info(f"[notify_new_update] 새로운 알림 emit 중 - UID: {uid}")
    socketio.emit("notification", {
        "uid": uid,
        "version": version,
        "description": description
    })

# 기기 클라이언트 인스턴스 생성
device = None
try:
    device = IoTDeviceClient(
        device_id=DEVICE_ID, model=MODEL, serial=SERIAL, version=VERSION, notification_callback=notify_new_update
    )
    logger.info(f"IoT 기기 클라이언트 초기화 완료: {DEVICE_ID}")
except Exception as e:
    logger.error(f"IoT 기기 클라이언트 초기화 실패: {e}")

# 정적 파일 디렉토리 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(os.path.dirname(current_dir), "frontend")

# 업데이트 이력 (In-memory 저장소)
update_history = []

# Websocket 대신 사용할 SSE 클라이언트 목록 >>?
# clients = []


@app.route("/")
def index():
    """프론트엔드 인덱스 페이지 제공"""
    return send_from_directory(static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """정적 파일 제공"""
    return send_from_directory(static_folder, path)


@app.route("/api/device/info", methods=["GET"])
def get_device_info():
    """기기 정보 반환"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500

    return jsonify(
        {
            "id": device.device_id,
            "model": device.attributes["model"],
            "serial": device.attributes["serial"],
            "version": device.attributes["version"],
            "lastUpdate": get_last_update(),
        }
    )


@app.route("/api/device/connection", methods=["GET"])
def check_connection():
    """블록체인 연결 상태 확인"""
    if not device:
        return jsonify({"connected": False}), 500

    try:
        connected = device.web3_http.is_connected()
        return jsonify({"connected": connected})
    except Exception as e:
        logger.error(f"블록체인 연결 확인 중 오류: {e}")
        return jsonify({"connected": False, "error": str(e)}), 500


@app.route("/api/device/updates", methods=["GET"])
def check_updates():
    if not device:
        return jsonify({"updates": [], "error": "기기 없음"}), 500
    try:
        updates = device.check_for_updates_http()
        return jsonify({"updates": updates})
    except Exception as e:
        logger.error(f"업데이트 확인 실패: {e}")
        return jsonify({"updates": [], "error": str(e)}), 500


# 디바이스 클라이언트 인스턴스를 반환하는 함수 추가
def get_device_client():
    """디바이스 클라이언트 인스턴스 반환"""
    global device
    if not device:
        try:
            device = IoTDeviceClient(
                device_id=DEVICE_ID, model=MODEL, serial=SERIAL, version=VERSION
            )
            logger.info(f"IoT 기기 클라이언트 초기화 완료: {DEVICE_ID}")
        except Exception as e:
            logger.error(f"IoT 기기 클라이언트 초기화 실패: {e}")
            return None
    return device


# 업데이트가 이미 설치되었는지 확인하는 함수 추가
def is_update_installed(uid):
    """업데이트가 이미 설치되었는지 확인"""
    for history_item in update_history:
        if history_item.get("uid") == uid:
            return True
    return False


@app.route("/api/device/notifications/stream")
def notification_stream():
    def generate():
        yield 'data: {"type": "connected", "message": "스트림 연결 성공"}\n\n'

        # BlockchainNotifier 대신 device_client 직접 사용
        previous_updates = set()
        while True:
            try:
                # device_client를 사용하여 업데이트 확인
                device_client = get_device_client()
                if device_client:
                    updates = device_client.check_for_updates_http()

                    # 에러 업데이트 필터링 추가
                    valid_updates = (
                        [u for u in updates if not u.get("isError", False)]
                        if updates
                        else []
                    )

                    # 새 업데이트가 있는지 확인
                    current_updates = (
                        set(update["uid"] for update in valid_updates)
                        if valid_updates
                        else set()
                    )
                    new_updates = current_updates - previous_updates

                    if new_updates:
                        for uid in new_updates:
                            update = next(
                                (u for u in valid_updates if u["uid"] == uid), None
                            )
                            if update:
                                logger.info(
                                    f"새 업데이트 알림: {uid}, 버전: {update.get('version')}"
                                )
                                yield f'data: {{"type": "new_update", "uid": "{uid}", "version": "{update.get("version", "")}", "description": "{update.get("description", "")}" }}\n\n'

                        previous_updates = current_updates

                # 이벤트 전송 간격
                time.sleep(5)

                # 연결 유지를 위한 하트비트
                yield 'data: {"type": "heartbeat"}\n\n'

            except Exception as e:
                logger.error(f"알림 스트림 오류: {e}")
                # 오류 메시지 대신 하트비트만 전송하여 클라이언트 연결 유지
                yield 'data: {"type": "heartbeat"}\n\n'
                time.sleep(5)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/device/updates/purchase", methods=["POST"])
def purchase_update():    
    """업데이트 구매"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500

    try:
        data = request.json
        uid = data.get("uid")
        price = int(data.get("price"))

        if not uid:
            return jsonify({"error": "업데이트 ID가 필요합니다"}), 400

        tx_hash = device.purchase_update(uid, price)

        return jsonify(
            {
                "success": True,
                "transaction": tx_hash.hex(),
                "message": f"업데이트 {uid} 구매 완료",
            }
        )
    except Exception as e:
        logger.error(f"업데이트 구매 중 오류: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/device/updates/install", methods=["POST"])
def install_update():
    """업데이트 설치"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500

    try:
        data = request.json
        uid = data.get("uid")

        if not uid:
            return jsonify({"error": "업데이트 ID가 필요합니다"}), 400

        # 업데이트 정보 가져오기
        updates = device.check_for_updates_http()
        update_info = next((u for u in updates if u["uid"] == uid), None)

        if not update_info:
            return jsonify({"error": f"업데이트 {uid}를 찾을 수 없습니다"}), 404

        # 권한 확인
        if not update_info.get("isAuthorized", False):
            return (
                jsonify(
                    {"error": "이 업데이트에 대한 권한이 없습니다. 먼저 구매하세요."}
                ),
                403,
            )

        # 업데이트 다운로드 및 설치 실행
        logger.info(f"업데이트 설치 시작: {uid}")
        result = device.download_update(update_info)

        if result["success"]:
            # 업데이트 이력에 추가
            add_update_history(
                uid,
                update_info["version"],
                update_info.get("description", ""),
                result.get("confirmation", {}).get("tx_hash", "unknown"),
            )

        return jsonify(result)

    except Exception as e:
        logger.error(f"업데이트 설치 중 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/device/history", methods=["GET"])
def get_update_history():
    """업데이트 이력 조회"""
    return jsonify({"history": update_history})


def get_last_update():
    """마지막 업데이트 정보 조회"""
    if update_history:
        return update_history[-1]
    return None


def add_update_history(uid, version, description="설명 없음", tx_hash="unknown"):
    """업데이트 이력 추가 - 개선된 버전"""
    update_history.append(
        {
            "uid": uid,
            "version": version,
            "timestamp": int(time.time()),
            "description": description,
            "tx_hash": tx_hash,
        }
    )
    logger.info(f"업데이트 이력에 추가됨: {uid}, 버전 {version}")


# @app.route("/api/device/events", methods=["GET"])
# def events():
#     """Server-Sent Events 엔드포인트"""

#     def stream():
#         yield 'data: {"message": "연결됨"}\n\n'

#         # 클라이언트 연결 유지
#         while True:
#             time.sleep(10)
#             yield 'data: {"keepalive": true}\n\n'

#     return Response(stream(), mimetype="text/event-stream")


# def send_notification(message):
#     """모든 클라이언트에게 알림 전송"""
#     if clients:
#         for client in clients[:]:
#             try:
#                 client.put(message)
#             except:
#                 clients.remove(client)


# 이벤트 리스너 시작
# if device:

#     def update_notification_handler(uid, version, description):
#         send_notification(
#             {
#                 "type": "update_available",
#                 "uid": uid,
#                 "version": version,
#                 "description": description,
#             }
#         )

#     device.start_update_listener(callback=update_notification_handler)


if __name__ == "__main__":
    import eventlet
    import eventlet.green.threading as threading

    def run_socketio():
        socketio.run(app, host="0.0.0.0", port=PORT, use_reloader=False)

    # Web3 이벤트 리스너 비동기 루틴 실행
    async def websocket_listener():
        await device._init_async_web3_socket_()
        await device.listen_for_updates()

    # eventlet용 green thread에서 실행
    threading.Thread(target=run_socketio).start()
    eventlet.spawn(asyncio.run, websocket_listener())

# if __name__ == "__main__":
#     async def init_websocket_listener():
#         await device._init_async_web3_socket_()
#         # device._load_contract()
#         await device.listen_for_updates()
    
#     loop = asyncio.new_event_loop()
#     threading.Thread(target=lambda: socketio.run(app, host="0.0.0.0", port=PORT, use_reloader=False), daemon=True).start()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(init_websocket_listener())
#     loop.run_forever()
