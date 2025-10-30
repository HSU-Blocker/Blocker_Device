import os
import numpy as np
import requests
import traceback
from speech.stt import WhisperSTT
from speech.tts import TTS
from speech.translator import TranslatorModule
from speaker.register_speaker import register_speaker_from_waveform, webm_bytes_to_numpy_waveform
from speaker.verify_speakers import verify_speakers_from_waveform


class VoiceService:
    """
    음성 인식(STT) + 번역 + 화자 인식 + LLM(Rasa) 통합 서비스 클래스
    """

    def __init__(self, initial_prompt=None, rasa_url="http://host.docker.internal:5005/webhooks/rest/webhook"):
        self.stt = WhisperSTT(initial_prompt=initial_prompt)
        self.tts = TTS()
        self.translator = TranslatorModule()
        self.embedding_path = os.path.join("data", "reference_multi.npy")
        self.rasa_url = rasa_url

    def register_speaker_from_webm(self, audio_bytes, speaker_name):
        """webm 음성을 numpy waveform으로 변환 후 화자 등록"""
        try:
            waveform = webm_bytes_to_numpy_waveform(audio_bytes, sample_rate=16000)
            success, name = register_speaker_from_waveform(speaker_name, waveform)
            return {"success": success, "speaker_name": name}
        except Exception as e:
            return {"success": False, "speaker_name": speaker_name, "error": str(e)}

    def stt_and_speaker_recognition(self, audio_bytes):
        """
        webm/wav bytes를 입력받아 STT(원문+번역) + 화자 인식 + LLM(Rasa) 결과를 통합 반환
        """
        try:
            # 1️. Whisper STT + 번역
            stt_result = self.stt.process_audio(audio_bytes)
            if "error" in stt_result:
                return stt_result

            transcribed_text = stt_result.get("transcribed_text", "")
            translated_text = stt_result.get("translated_text", "")
            detected_lang = stt_result.get("detected_lang", "unknown")

            # 2️. numpy waveform 변환 → 화자 인식
            np_waveform = webm_bytes_to_numpy_waveform(audio_bytes, sample_rate=16000)
            best_name, best_similarity, is_match = verify_speakers_from_waveform(np_waveform)
            predicted_speaker = best_name or "unknown"

            # 3️. 화자 유형 판단
            if is_match:
                speaker_type = "owner" if best_name == "owner" else "known"
            else:
                speaker_type = "unknown"

            # # 4️. Rasa LLM 호출
            # rasa_response_text = None
            # try:
            #     payload = {"sender": speaker_type, "message": translated_text}
            #     rasa_response = requests.post(self.rasa_url, json=payload, timeout=10)
            #     if rasa_response.ok:
            #         data = rasa_response.json()
            #         rasa_texts = [m.get("text", "") for m in data if "text" in m]
            #         rasa_response_text = " ".join(filter(None, rasa_texts))
            #     else:
            #         rasa_response_text = f"Rasa error: {rasa_response.status_code}"
            # except Exception as e:
            #     rasa_response_text = f"Rasa 호출 실패: {str(e)}"

            # 최종 결과 반환
            return {
                "transcribed_text": transcribed_text,
                # "translated_text": translated_text,
                "detected_lang": detected_lang,
                "is_match": is_match,
                "speaker_type": speaker_type,
                "predicted_speaker": predicted_speaker,
                # "rasa_response": rasa_response_text
            }

        except Exception as e:
            print(f"[VoiceService ERROR] {e}\n{traceback.format_exc()}")
            return {"error": str(e)}
