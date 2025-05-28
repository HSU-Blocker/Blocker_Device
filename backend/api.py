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
DEVICE_ID = os.getenv("DEVICE_ID", "blocker_device_001")
MODEL = os.getenv("DEVICE_MODEL", "VS500")
SERIAL = os.getenv("DEVICE_SERIAL", "KMHEM42APXA752012")
VERSION = os.getenv("DEVICE_VERSION", "1.0.0")
PORT = int(os.getenv("DEVICE_API_PORT", 5002))
MANUFACTURER_API_URL = os.getenv("MANUFACTURER_API_URL")

# 알림 콜백 함수 (IoTDeviceClient에서 업데이트가 있을 때 호출)
# socketio.emit을 사용하여 클라이언트에게 알림을 전송
def notify_new_update(uid, version, description):
    logger.info(f"[notify_new_update] 새로운 알림 emit 중 - UID: {uid}")
    socketio.emit("notification", {
        "type": "new_update",
        "data": {
            "uid": uid,
            "version": version,
            "description": description
        }
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

    # 설치된 업데이트 이력에서 마지막 업데이트 정보 확인
    installation_logs = device.get_update_history()
    last_update = installation_logs[0] if installation_logs else None

    # 기기의 현재 버전은 마지막 업데이트의 버전을 사용
    current_version = last_update["version"] if last_update else device.attributes["version"]
    last_update_timestamp = last_update["timestamp"] if last_update else None
    last_update_uid = last_update["uid"] if last_update else None

    # 마지막 업데이트 description만 반환
    if last_update:
        try:
            update_info = device.contract_http.functions.getUpdateInfo(last_update["uid"]).call()
            last_update_description = update_info[3]  # description 필드
        except Exception as e:
            logger.error(f"마지막 업데이트 description 조회 실패: {e}")
            last_update_description = None
    else:
        last_update_description = None

    return jsonify(
        {
            "id": device.device_id,
            "model": device.attributes["model"],
            "serial": device.attributes["serial"],
            "version": current_version,
            "lastUpdate": last_update_timestamp,
            "uid": last_update_uid,
            "description": last_update_description,
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
            error_msg = result.get("message", "")
            if "잔액이 부족합니다" in error_msg:
                return jsonify({
                    "error": "계정 잔액이 부족합니다. 필요한 금액을 확인해주세요.",
                    "details": error_msg
                }), 400
            elif "Already purchased" in error_msg:
                return jsonify({
                    "error": "구매할 수 없거나 이미 구매한 업데이트입니다.",
                    "details": error_msg
                }), 400
            else:
                return jsonify({
                    "error": "업데이트 구매에 실패했습니다.",
                    "details": error_msg
                }), 500

        return jsonify({
            "success": True,
            "transaction": result["tx_hash"],
            "message": f"업데이트 {uid} 구매 완료"
        })

    except ValueError as e:
        logger.error(f"업데이트 구매 중 값 오류: {e}")
        return jsonify({"error": "잘못된 입력값입니다.", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"업데이트 구매 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "업데이트 구매 중 오류가 발생했습니다.", "details": str(e)}), 500

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

        # 실패 시 구체적인 오류 메시지 반환
        if not result["success"]:
            error_message = result.get("message", "알 수 없는 오류")
            logger.error(f"설치 실패: {error_message}")

            # 오류 메시지 분석하여 적절한 메시지 생성
            if "대칭키 복호화 실패" in error_message:
                message = "대칭키 복호화 실패, 환불되었습니다."
            elif "해시 검증 실패" in error_message:
                message = "업데이트 파일 무결성 검증 실패, 환불되었습니다."
            elif "다운로드" in error_message:
                message = "업데이트 파일 다운로드 실패, 환불되었습니다."
            else:
                message = "업데이트 설치 실패, 환불되었습니다."

            return jsonify({
                "success": False,
                "error": message,  # 사용자에게 보여질 메시지
                "details": error_message,  # 디버깅용 상세 에러
                "message": message  # 이전 버전 호환성 유지
            }), 500

        return jsonify(result)

    except Exception as e:
        logger.error(f"업데이트 설치 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": "업데이트 설치 중 오류가 발생했습니다.",
            "error": str(e)
        }), 500

@app.route("/api/device/history", methods=["GET"])
def get_update_history():
    """설치된 업데이트와 환불된 업데이트 이력 조회"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500
    try:
        # 설치된 업데이트 목록
        installation_logs = device.get_update_history()
        logger.info(f"[get_update_history] 설치된 업데이트 UID 목록: {[log['uid'] for log in installation_logs]}")
        # 환불된 업데이트 목록
        refunded_updates = device.get_refunded_updates()
        logger.info(f"[get_update_history] 환불된 업데이트 UID 목록: {[u['uid'] for u in refunded_updates]}")

        update_history = []
        seen_uids = set()

        # 설치된 업데이트 처리 (가격, 설명, 버전 포함)
        for log in installation_logs:
            uid = log["uid"]
            if uid in seen_uids:
                continue
            # 블록체인에서 가격, 설명, 버전 정보 가져오기
            try:
                update_info = device.contract_http.functions.getUpdateInfo(uid).call()
                price_wei = int(update_info[4])
                price_eth = float(device.web3_http.from_wei(price_wei, "ether"))
                description = update_info[3]
                version = update_info[5]
            except Exception as e:
                logger.error(f"업데이트 정보 조회 실패(uid={uid}): {e}")
                price_eth = None
                description = None
                version = None
            item = {
                "uid": uid,
                "version": version,
                "description": description,
                "price_eth": price_eth,
                "isInstalled": True,
                "isRefunded": False,
                "installedAt": log.get("timestamp"),  # 블록체인에서 가져온 시각
                "refundedAt": None,
            }
            update_history.append(item)
            seen_uids.add(uid)

        # 환불만 된 항목(설치 안된 것) 추가 (가격, 설명, 버전 포함)
        for refund in refunded_updates:
            uid = refund["uid"]
            item = {
                "uid": uid,
                "isInstalled": False,
                "isRefunded": True,
                "installedAt": None,
                "refundedAt": refund.get("purchasedAt"),  # purchasedAt을 refundedAt으로 사용
                "price_eth": float(device.web3_http.from_wei(int(refund.get("price", 0)), "ether")),
                "description": refund.get("description"),
                "version": refund.get("version")
            }
            update_history.append(item)

        # 모든 이벤트를 발생 시각순으로 정렬
        def get_event_time(item):
            if item["isInstalled"]:
                return item["installedAt"] or 0
            else:
                return item["refundedAt"] or 0  # refundedAt을 기준으로 정렬
        
        # 시각 기준 정렬 (최신순)
        update_history.sort(key=get_event_time, reverse=True)
        logger.info(f"[get_update_history] 정렬된 이력: {[(item['uid'], get_event_time(item)) for item in update_history]}")
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
