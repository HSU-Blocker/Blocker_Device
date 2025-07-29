import requests
import logging
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# ===== 차량 및 업데이트 관련 액션 =====
# 업데이트 시작은 아직 안함
DEVICE_UPDATES_URL = "http://device:5002/api/device/updates"
DEVICE_INSTALL_URL = "http://device:5002/api/device/updates/install"
CAR_API_URL = "http://192.168.0.15:5555/command" 


logger = logging.getLogger(__name__)

class ActionUpdateStart(Action):
    def name(self):
        return "action_update_start"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            logger.info("[update_start] 차량 업데이트 시작: 1. 업데이트 목록 조회")
    
            # 최신 업데이트 목록 확인
            response = requests.get(DEVICE_UPDATES_URL, timeout=5)
            if response.status_code != 200:
                dispatcher.utter_message(text="업데이트 목록을 가져오지 못했습니다.")
                logger.error(f"[update_start] 업데이트 목록 조회 실패: {response.status_code}")
                return []
            
            data = response.json()
            updates = data.get("updates", [])
            # logger.info(f"[update_start] 최신 업데이트 목록 조회: {data}")
            # logger.info(f"[update_start] 업데이트 개수: {updates}")
            if not updates:
                dispatcher.utter_message(text="설치할 수 있는 업데이트가 없습니다.")
                logger.info("[update_start] 설치 가능한 업데이트가 없습니다.")
                return []

            latest = updates[0]
            uid = latest.get("uid")
            logger.info(f"[update_start] 최신 업데이트 UID: {uid}")
            if not uid:
                dispatcher.utter_message(text="업데이트 UID를 확인할 수 없습니다.")
                return []

            # 설치 요청 전송
            install_resp = requests.post(
                DEVICE_INSTALL_URL,
                json={"uid": uid},
                timeout=10
            )

            if install_resp.ok:
                dispatcher.utter_message(text=f"업데이트({uid})를 성공적으로 설치했습니다.")
                logger.info(f"[update_start] 업데이트 설치 성공: {uid}")
            else:
                msg = install_resp.json().get("message", "업데이트 실패")
                dispatcher.utter_message(text=f"업데이트 실패: {msg}")
                logger.error(f"[update_start] 업데이트 설치 실패: {msg}, 상태 코드: {install_resp.status_code}")    

        except Exception as e:
            logger.error(f"[update_start] 예외 발생: {e}")
            dispatcher.utter_message(text="업데이트 중 오류가 발생했습니다.")
        return []
    

class ActionUpdateInstallByUID(Action):
    def name(self):
        return "action_update_install_by_uid"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        uid = tracker.get_slot("update_uid")
        if not uid:
            logger.error("[ActionUpdateInstallByUID] 설치할 업데이트 UID가 없습니다.")
            dispatcher.utter_message(text="설치할 업데이트 UID를 찾을 수 없습니다.")
            return []

        try:
            install_resp = requests.post(
                "http://device:5002/api/device/updates/install",
                json={"uid": uid},
                timeout=10
            )
            if install_resp.status_code == 200:
                dispatcher.utter_message(text=f"업데이트({uid})를 설치했습니다.")
            else:
                msg = install_resp.json().get("message", "업데이트 실패")
                dispatcher.utter_message(text=f"업데이트 실패: {msg}")
        except Exception as e:
            dispatcher.utter_message(text="업데이트 중 오류가 발생했습니다.")
            print(f"[ActionUpdateInstallByUID] 예외: {e}")
        return [] 


class ActionUpdateList(Action):
    def name(self):
        return "action_update_list"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        logger.info("[action_update_list] 차량에서 업데이트 목록 조회 시도")
        try:
            # docker-compose 네트워크 이름 사용
            response = requests.get(DEVICE_UPDATES_URL, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"[action_update_list] 업데이트 목록 조회 실패: {response.status_code}")
                dispatcher.utter_message(text="차량에서 업데이트 목록을 불러오지 못했습니다.")
                return []

            data = response.json()
            logger.info(f"[action_update_list] 업데이트 목록 조회 성공: {data}")
            updates = data.get("updates", [])

            if not updates:
                logger.info("[action_update_list] 설치 가능한 업데이트가 없습니다.")
                dispatcher.utter_message(text="현재 설치 가능한 업데이트가 없습니다.")
                return []

            # 업데이트 리스트 출력 포맷
            update_texts = []
            for update in updates:
                uid = update.get("uid", "-")
                version = update.get("version", "-")
                description = update.get("description", "-")
                update_texts.append(f"UID: {uid}, 버전: {version}, 설명: {description}")

            message = "조회된 업데이트 목록입니다:\n" + "\n".join(update_texts)
            dispatcher.utter_message(text=message)
            logger.info(f"[action_update_list123] 업데이트 목록: {update_texts}")

            payload = {
                "command": "say",
                "target": message,
            }
            response = requests.post(CAR_API_URL, json=payload, timeout=3)
            
            if response.status_code == 200:
                logger.info("[acion_update_list] 업데이트 리스트 조회")
            else:
                logger.error(f"[action_go_hospital] 오류 응답 코드: {response.status_code}")
        except Exception as e:
            print(f"[action_update_list] 오류: {e}")
            dispatcher.utter_message(text="업데이트 목록을 조회하는 중 오류가 발생했습니다.")
        return []


class ActionDriveForward(Action):
    def name(self):
        return "action_drive_forward"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            logger.info("[action_drive_forward] 차량 직진 명령 전송")
            response = requests.post(CAR_API_URL, json={"command": "start"}, timeout=3)
            if response.status_code == 200:
                logger.info("[action_drive_forward] 차량 직진 명령 성공")
                dispatcher.utter_message(text="차량이 직진합니다.")
            else:
                logger.error(f"[action_drive_forward] 차량 직진 명령 실패: {response.status_code}")
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            logger.error(f"[action_drive_forward] 예외 발생: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionStop(Action):
    def name(self):
        return "action_stop"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            print("[action_stop] 차량 정지")
            response = requests.post(CAR_API_URL, json={"command": "stop"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="차량을 정지합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_stop] 오류: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionShutdown(Action):
    def name(self):
        return "action_shutdown"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            payload = {
                "command": "shutdown",
                "text": "shutdown."
            }
            logger.info("[action_shutdown] 차량 셧다운 명령 전송")
            response = requests.post(CAR_API_URL, json={"command": "shutdown"}, timeout=3)
            if response.status_code == 200:
                logger.info("[action_shutdown] 차량 셧다운 명령 성공")
                dispatcher.utter_message(text="차량을 셧다운합니다.")
            else:
                logger.error(f"[action_shutdown] 차량 셧다운 명령 실패: {response.status_code}")
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            logger.error(f"[action_shutdown] 예외 발생: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionGoHospital(Action):
    def name(self):
        return "action_go_hospital"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            payload = {
                "command": "go_to",
                "target": "hospital"
            }
            response = requests.post(CAR_API_URL, json=payload, timeout=3)
            
            if response.status_code == 200:
                logger.info("[action_go_hospital] 차량이 병원으로 이동")
                dispatcher.utter_message(text="병원으로 이동합니다.")
            else:
                logger.error(f"[action_go_hospital] 오류 응답 코드: {response.status_code}")
                dispatcher.utter_message(text="차량과의 통신에 실패했습니다.")
        except Exception as e:
            logger.error(f"[action_go_hospital] 예외 발생: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionGoCompany(Action):
    def name(self):
        return "action_go_company"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            payload = {
                "command": "go_to",
                "target": "company"
            }
            response = requests.post(CAR_API_URL, json=payload, timeout=3)
            
            if response.status_code == 200:
                logger.info("[action_go_company] 차량이 회사로 이동")
                dispatcher.utter_message(text="회사로 이동합니다.")
            else:
                logger.error(f"[action_go_company] 오류 응답 코드: {response.status_code}")
                dispatcher.utter_message(text="차량과의 통신에 실패했습니다.")
        except Exception as e:
            logger.error(f"[action_go_company] 예외 발생: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []
    

class ActionGoUniversity(Action):
    def name(self):
        return "action_go_university"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            payload = {
                "command": "go_to",
                "target": "university"
            }
            response = requests.post(CAR_API_URL, json=payload, timeout=3)
            
            if response.status_code == 200:
                logger.info("[action_go_university] 차량이 대학교로 이동")
                dispatcher.utter_message(text="대학교로 이동합니다.")
            else:
                logger.error(f"[action_go_university] 오류 응답 코드: {response.status_code}")
                dispatcher.utter_message(text="차량과의 통신에 실패했습니다.")
        except Exception as e:
            logger.error(f"[action_go_university] 예외 발생: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []


# ===== fallback: LLM =====

from transformers import pipeline


class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        user_text = tracker.latest_message.get('text')
        logger.info(f"[action_default_fallback] 사용자 입력: {user_text}")

        try:
            response = requests.post(
                "http://llm_fallback:5000/llm",
                json={"prompt": user_text},
                timeout=60
            )
            data = response.json()
            if response.status_code != 200 or "response" not in data:
                logger.error(f"[action_default_fallback] LLM 응답 오류: {data}")
                dispatcher.utter_message(text="죄송합니다. 서버 문제로 지금은 답변할 수 없습니다.")
                return []
            logger.info("[action_default_fallback] LLM 서버 응답 성공")
            
            generated = data.get("response")
            logger.info(f"[action_default_fallback] LLM 응답: {generated}")
            dispatcher.utter_message(text=generated)

        except Exception as e:
            logger.error(f"[action_default_fallback] LLM 서버 오류: {e}")
            dispatcher.utter_message(text="죄송합니다. 지금은 답변할 수 없습니다.")
        
        return []