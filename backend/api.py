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

# 프론트엔드 라우팅
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

    # 구매 목록에서 마지막 구매한 업데이트 정보 확인
    purchased_updates = device.get_purchased_updates()
    last_update = purchased_updates[0] if purchased_updates else None

    return jsonify(
        {
            "id": device.device_id,
            "model": device.attributes["model"],
            "serial": device.attributes["serial"],
            "version": device.attributes["version"],
            "lastUpdate": last_update,
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
        # 설치된 업데이트 uid 목록 구하기
        installation_logs = device.get_update_history()
        installed_uids = {log["uid"] for log in installation_logs}
        # 설치되지 않은 업데이트만 반환
        not_installed_updates = [u for u in updates if u["uid"] not in installed_uids]
        return jsonify({"updates": not_installed_updates})
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
    """업데이트를 구매했는지 확인"""
    if not device:
        return False
    
    purchased = device.get_purchased_updates()
    return any(item.get("uid") == uid for item in purchased)

@app.route("/api/device/updates/purchase", methods=["POST"])
def purchase_update():    
    """업데이트 구매"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500

    try:
        data = request.json
        uid = data.get("uid")
        price = data.get("price")

        if not uid:
            return jsonify({"error": "업데이트 ID가 필요합니다"}), 400

        if not price:
            return jsonify({"error": "가격이 필요합니다"}), 400

        result = device.purchase_update(uid, price)
        
        if not result.get("success"):
            return jsonify({"error": "구매 실패", "details": result.get("message", "")}), 500

        return jsonify({
            "success": True,
            "transaction": result["tx_hash"],
            "message": f"업데이트 {uid} 구매 완료"
        })

    except ValueError as e:
        logger.error(f"업데이트 구매 중 값 오류: {e}")
        return jsonify({"error": str(e)}), 400
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

        # 업데이트 다운로드 및 설치 실행
        logger.info(f"업데이트 설치 시작: {uid}")
        result = device.download_update(update_info)

        return jsonify(result)

    except Exception as e:
        logger.error(f"업데이트 설치 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/device/history", methods=["GET"])
def get_update_history():
    """업데이트 구매/설치 이력 조회"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500
    
    try:
        # 구매한 업데이트 목록 조회
        purchased_updates = device.get_purchased_updates()
        logger.info(f"[get_update_history] 구매한 업데이트 목록: {json.dumps(purchased_updates, indent=2)}")
        
        # 설치된 업데이트 목록 조회
        installation_logs = device.get_update_history()
        logger.info(f"[get_update_history] 설치된 업데이트 목록: {json.dumps(installation_logs, indent=2)}")
        installed_uids = {log["uid"] for log in installation_logs}
        
        # 구매 목록에 설치 상태 추가
        update_history = []
        seen_uids = set()
        # 최신순 정렬된 purchased_updates를 역순으로 순회하며 중복 제거
        for update in purchased_updates:
            if update["uid"] in seen_uids:
                continue
            update_info = update.copy()  # 원본 데이터 복사
            update_info["isPurchased"] = True  # 구매 목록에 있으므로 항상 True
            update_info["isInstalled"] = update["uid"] in installed_uids
            
            # wei를 ETH로 변환하여 추가
            price_wei = int(update.get("price", 0))
            price_eth = device.web3_http.from_wei(price_wei, "ether")
            update_info["price_wei"] = price_wei
            update_info["price_eth"] = float(price_eth)
            
            # 설치 정보가 있는 경우 설치 시간 추가
            if update_info["isInstalled"]:
                install_log = next(log for log in installation_logs if log["uid"] == update["uid"])
                update_info["installedAt"] = install_log.get("timestamp")
            
            update_history.append(update_info)
            seen_uids.add(update["uid"])
            
        # 시간순 정렬 (최신순)
        update_history.sort(key=lambda x: x.get("installedAt", 0) or x.get("timestamp", 0), reverse=True)
        
        logger.info(f"[get_update_history] 최종 반환할 업데이트 이력: {json.dumps(update_history, indent=2)}")
        return jsonify({"history": update_history})
    except Exception as e:
        logger.error(f"업데이트 이력 조회 실패: {e}")
        return jsonify({"error": str(e)}), 500

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
