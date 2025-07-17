import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
CAR_API_URL = "http://192.168.0.15:8888/command" 

# ===== 차량 및 업데이트 관련 액션 =====
# 업데이트 시작은 아직 안함
class ActionUpdateStart(Action):
    def name(self):
        return "action_update_start"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        speaker = tracker.get_slot("speaker") or "unknown"
        print(f"[action_update_start] speaker: {speaker}")

        if speaker == "owner":
                    dispatcher.utter_message(text="차주님, 차량 소프트웨어를 업데이트 합니다.")
        else:
            dispatcher.utter_message(text="죄송합니다. 차주가 아니므로 차량 업데이트를 진행할 수 없습니다.")
        return []

class ActionUpdateList(Action):
    def name(self):
        return "action_update_list"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        print("[action_update_list] 차량에서 업데이트 목록 조회 시도")
        try:
            # docker-compose 네트워크 이름 사용
            response = requests.get("http://device:5002/api/device/updates", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(text="차량에서 업데이트 목록을 불러오지 못했습니다.")
                return []

            data = response.json()
            updates = data.get("updates", [])

            if not updates:
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

        except Exception as e:
            print(f"[action_update_list] 오류: {e}")
            dispatcher.utter_message(text="업데이트 목록을 조회하는 중 오류가 발생했습니다.")

        return []

# 차량 ECU HTTP API
CAR_API_URL = "http://192.168.0.15:8888/command" 

class ActionDriveForward(Action):
    def name(self):
        return "action_drive_forward"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            print("[action_drive_forward] 차량 직진")
            response = requests.post(CAR_API_URL, json={"command": "start"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="차량이 직진합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_drive_forward] 오류: {e}")
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
            print("[action_shutdown] 차량 셧다운")
            response = requests.post(CAR_API_URL, json={"command": "shutdown"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="차량을 셧다운합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_shutdown] 오류: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionGoHospital(Action):
    def name(self):
        return "action_go_hospital"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            print("[action_go_hospital] 병원으로 이동")
            response = requests.post(CAR_API_URL, json={"command": "go_to hospital"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="병원으로 이동합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_go_hospital] 오류: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionGoCompany(Action):
    def name(self):
        return "action_go_company"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            print("[action_go_company] 회사로 이동")
            response = requests.post(CAR_API_URL, json={"command": "go_to company"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="회사로 이동합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_go_company] 오류: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []

class ActionGoUniversity(Action):
    def name(self):
        return "action_go_university"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        try:
            print("[action_go_university] 대학교로 이동")
            response = requests.post(CAR_API_URL, json={"command": "go_to university"}, timeout=3)
            if response.status_code == 200:
                dispatcher.utter_message(text="대학교로 이동합니다.")
            else:
                dispatcher.utter_message(text="차량과 통신에 실패했습니다.")
        except Exception as e:
            print(f"[action_go_university] 오류: {e}")
            dispatcher.utter_message(text="차량과 통신 중 오류가 발생했습니다.")
        return []


# ===== fallback: LLM =====

from transformers import pipeline
pipe = pipeline("text-generation", model="distilgpt2", device=-1)

class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        user_text = tracker.latest_message.get('text')
        print(f"[action_default_fallback] fallback 요청: {user_text}")

        try:
            response = requests.post(
                "http://llm_fallback:5000/llm",
                json={"prompt": user_text},
                timeout=5
            )
            generated = response.json()[0]["generated_text"]
            print(f"[action_default_fallback] LLM 응답: {generated}")
            dispatcher.utter_message(text=generated)

        except Exception as e:
            print(f"[action_default_fallback] LLM 서버 오류: {e}")
            dispatcher.utter_message(text="죄송합니다. 지금은 답변할 수 없습니다.")
        
        return []