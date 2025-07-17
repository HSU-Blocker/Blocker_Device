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

# 알림 저장소 (메모리)
notifications = []
notification_id_counter = 1


# 알림 등록 함수 (emit + 저장)
def notify_new_update(uid, version, description):
    global notification_id_counter
    logger.info(f"[notify_new_update] 새로운 알림 emit 중 - UID: {uid}")
    notification = {
        "id": notification_id_counter,
        "timestamp": int(time.time()),
        "type": "new_update",
        "data": {"uid": uid, "version": version, "description": description},
    }
    notifications.append(notification)
    notification_id_counter += 1
    socketio.emit("notification", notification)


# 기기 클라이언트 인스턴스 생성
from speech.stt import WhisperSTT

whisper_stt_instance = None

device = None
try:
    device = IoTDeviceClient(
        device_id=DEVICE_ID,
        model=MODEL,
        serial=SERIAL,
        version=VERSION,
        notification_callback=notify_new_update,
    )
    logger.info(f"IoT 기기 클라이언트 초기화 완료: {DEVICE_ID}")
    # WhisperSTT 인스턴스도 서버 시작 시 미리 초기화 (모델 캐시 목적)
    logger.info("[WhisperSTT] Whisper 모델 다운로드 및 초기화 시작...")
    whisper_stt_instance = WhisperSTT(
        initial_prompt="음성이 'Hey Blocker' 또는 '헤이 블로커'로 시작됩니다."
    )
    logger.info("WhisperSTT 인스턴스 초기화 완료 (모델 캐시)")
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
    installation_logs = device.get_owner_update_history()
    last_update = installation_logs[0] if installation_logs else None

    # 기기의 현재 버전은 마지막 업데이트의 버전을 사용
    current_version = (
        last_update["version"] if last_update else device.attributes["version"]
    )
    last_update_timestamp = last_update["installedAt"] if last_update else None
    last_update_uid = last_update["uid"] if last_update else None

    # 마지막 업데이트 description만 반환
    if last_update:
        last_update_description = last_update["description"]
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
                return (
                    jsonify(
                        {
                            "error": "계정 잔액이 부족합니다. 필요한 금액을 확인해주세요.",
                            "details": error_msg,
                        }
                    ),
                    400,
                )
            elif "Already purchased" in error_msg:
                return (
                    jsonify(
                        {
                            "error": "구매할 수 없거나 이미 구매한 업데이트입니다.",
                            "details": error_msg,
                        }
                    ),
                    400,
                )
            else:
                return (
                    jsonify(
                        {"error": "업데이트 구매에 실패했습니다.", "details": error_msg}
                    ),
                    500,
                )

        return jsonify(
            {
                "success": True,
                "transaction": result["tx_hash"],
                "message": f"업데이트 {uid} 구매 완료",
            }
        )

    except ValueError as e:
        logger.error(f"업데이트 구매 중 값 오류: {e}")
        return jsonify({"error": "잘못된 입력값입니다.", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"업데이트 구매 중 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return (
            jsonify(
                {"error": "업데이트 구매 중 오류가 발생했습니다.", "details": str(e)}
            ),
            500,
        )


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

            return (
                jsonify(
                    {
                        "success": False,
                        "error": message,  # 사용자에게 보여질 메시지
                        "details": error_message,  # 디버깅용 상세 에러
                        "message": message,  # 이전 버전 호환성 유지
                    }
                ),
                500,
            )

        return jsonify(result)

    except Exception as e:
        logger.error(f"업데이트 설치 중 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return (
            jsonify(
                {
                    "success": False,
                    "message": "업데이트 설치 중 오류가 발생했습니다.",
                    "error": str(e),
                }
            ),
            500,
        )


@app.route("/api/device/history", methods=["GET"])
def get_update_history():
    """설치된 업데이트와 환불된 업데이트 이력 조회 (device_client 위임)"""
    if not device:
        return jsonify({"error": "디바이스 초기화에 실패했습니다"}), 500
    try:
        update_history = device.get_owner_update_history()
        return jsonify({"history": update_history})
    except Exception as e:
        logger.error(f"업데이트 이력 조회 실패: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """since=<id> 이후의 알림 목록 반환"""
    since_id = request.args.get("since", default=0, type=int)
    # since_id보다 큰 id의 알림만 반환
    filtered = [n for n in notifications if n["id"] > since_id]
    return jsonify({"notifications": filtered})


from service.voice_service import VoiceService
voice_service = VoiceService()

@app.route("/api/device/voice/register", methods=["POST"])
def api_voice_register():
    """
    사용자 등록용 음성 파일(webm)과 user_name을 받아 등록 처리 후 결과 반환
    """
    if "audio" not in request.files or "user_name" not in request.form:
        return jsonify({"success": False, "error": "audio file or user_name missing"}), 400
    audio_file = request.files["audio"]
    user_name = request.form["user_name"]
    audio_bytes = audio_file.read()
    result = voice_service.register_speaker_from_webm(audio_bytes, user_name)
    logger.info(f"/api/device/voice/register 응답 결과: {result}")
    return jsonify(result)

def get_stt_and_speaker_result(audio_bytes):
    """stt_and_speaker_recognition 결과를 캐싱해서 반환"""
    return voice_service.stt_and_speaker_recognition(audio_bytes)

llm_result_cache = {}

def call_llm_and_store(result, speaker_key):
    logging.info(f"[LLM] 호출 시작 - speaker_key: {speaker_key}, payload: {{'sender': {result.get('speaker_type')}, 'message': {result.get('translated_text')}}}")
    llm_payload = {
        "sender": result.get("speaker_type"),
        "message": result.get("translated_text")
    }
    try:
        rasa_response = requests.post(
            "http://rasa:5005/webhooks/rest/webhook",
            json=llm_payload,
            timeout=5
        )
        if rasa_response.ok:
            rasa_output = rasa_response.json()
            rasa_text = " ".join([msg["text"] for msg in rasa_output if "text" in msg])
            llm_result_cache[speaker_key] = {"text": rasa_text}
            logging.info(f"[LLM] 성공 - speaker_key: {speaker_key}, status: {rasa_response.status_code}, response: {rasa_output}")
        else:
            llm_result_cache[speaker_key] = {"error": f"Rasa error: {rasa_response.status_code}"}
            logging.error(f"[LLM] 실패 - speaker_key: {speaker_key}, status: {rasa_response.status_code}, response: {rasa_response.text}")
    except Exception as e:
        llm_result_cache[speaker_key] = {"error": str(e)}
        import traceback
        logging.error(f"[LLM] 예외 발생 - speaker_key: {speaker_key}, error: {e}\n{traceback.format_exc()}")

@app.route("/api/device/voice/stt", methods=["POST"])
def api_voice_stt():
    """
    프론트에서 webm 음성 파일을 받아 원문 텍스트, 언어감지, 화자 인식 결과 반환 (프론트 전용)
    LLM 결과는 별도 API로 제공
    """
    if "audio" not in request.files:
        return jsonify({"error": "audio file missing"}), 400
    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    result = get_stt_and_speaker_result(audio_bytes)

    response = {
        "transcribed_text": result.get("transcribed_text"),
        "detected_lang": result.get("detected_lang"),
        "is_match": bool(result.get("is_match")),
        "predicted_speaker": result.get("predicted_speaker")
    }
    # speaker_key는 predicted_speaker + timestamp 등으로 유니크하게 생성 가능
    speaker_key = f"{result.get('predicted_speaker','unknown')}_{int(time.time()*1000)}"
    response["llm_key"] = speaker_key
    # LLM 호출을 백그라운드로 실행
    logging.info(f"LLM 호출 스레드 시작 - speaker_key: {speaker_key}")
    threading.Thread(target=call_llm_and_store, args=(result, speaker_key)).start()
    return jsonify(response)


@app.route("/api/device/voice/llm_result", methods=["GET"])
def get_llm_result():
    """
    프론트가 llm_key로 LLM 결과를 가져가는 API
    """
    llm_key = request.args.get("llm_key")
    if not llm_key:
        return jsonify({"error": "llm_key is required"}), 400
    result = llm_result_cache.get(llm_key)
    if result is None:
        return jsonify({"status": "pending"})
    return jsonify({"llm_result": result})


# @app.route("/api/device/voice/tts", methods=["POST"])
# def api_voice_tts():
#     """
#     프론트에서 webm 음성 파일을 받아 STT→번역 후, 변환된 텍스트로 TTS 음성(wav) 파일을 반환
#     """
#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400
#     audio_file = request.files["audio"]
#     import tempfile

#     with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
#         tmp.write(audio_file.read())
#         tmp_path = tmp.name
#     try:
#         from pipeline import SpeechService
#         from tts import TTS

#         service = SpeechService()
#         with open(tmp_path, "rb") as f:
#             audio_bytes = f.read()
#         stt_text, detected_lang = service.audio_to_text(audio_bytes)
#         tts = TTS()
#         tts_audio = tts.synthesize(stt_text, language=detected_lang or "ko")
#         # 음성(wav) 파일을 바이너리로 직접 반환
#         from flask import send_file
#         import io as _io

#         return send_file(
#             _io.BytesIO(tts_audio),
#             mimetype="audio/wav",
#             as_attachment=True,
#             download_name="result.wav",
#         )
#     finally:
#         import os

#         os.remove(tmp_path)

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