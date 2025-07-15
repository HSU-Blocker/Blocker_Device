import os
from speech.stt import WhisperSTT, webm_bytes_to_tensor_waveform
from speech.tts import TTS
from speech.translator import TranslatorModule
from speaker.register_speaker import register_speaker_from_waveform, webm_bytes_to_numpy_waveform
from speaker.verify_speakers import verify_speakers_from_waveform
import numpy as np

class VoiceService:
    def __init__(self, initial_prompt=None):
        self.stt = WhisperSTT(initial_prompt=initial_prompt)
        self.tts = TTS()
        self.translator = TranslatorModule()
        self.embedding_path = os.path.join("data", "reference_multi.npy")

    def register_speaker_from_webm(self, audio_bytes, speaker_name):
        """
        음성을 입력 받아 npy에 등록
        성공/실패 여부와 user_name을 반환
        """
        try:
            waveform = webm_bytes_to_numpy_waveform(audio_bytes, sample_rate=16000)
            success, name = register_speaker_from_waveform(speaker_name, waveform)
            return {"success": success, "speaker_name": name}
        except Exception as e:
            return {"success": False, "speaker_name": speaker_name, "error": str(e)}

    def stt_and_speaker_recognition(self, audio_bytes):
        """
        webm/wav bytes 입력을 받아 STT(+번역)와 화자 인식 결과를 통합 반환
        - audio_bytes: webm/wav 등 bytes
        - return: dict (transcribed_text, detected_lang, translated_text, speaker_type, predicted_speaker)
        """
        try:
            # 1. 화자 인식용 numpy waveform
            np_waveform = webm_bytes_to_numpy_waveform(audio_bytes, sample_rate=16000)

            # 2. STT용 torch tensor waveform
            torch_waveform = webm_bytes_to_tensor_waveform(audio_bytes, sample_rate=16000)
            if torch_waveform.dim() == 1:
                torch_waveform = torch_waveform.unsqueeze(0)

            # 3. STT (원문 텍스트)
            transcribed_text = self.stt.transcribe(torch_waveform)
            detected_lang = getattr(self.stt, 'last_detected_language', None)

            # 4. 번역 (영어)
            translated_text = self.stt.translate_to_english(torch_waveform)

            # 5. 화자 검증 및 예상화자
            best_name, best_similarity, is_match = verify_speakers_from_waveform(np_waveform)
            predicted_speaker = best_name
            if is_match:
                if best_name == "owner":
                    speaker_type = "owner"
                else:
                    speaker_type = "known"
            else:
                speaker_type = "unknown"

            return {
                "transcribed_text": transcribed_text,
                "detected_lang": detected_lang,
                "translated_text": translated_text,
                "is_match": is_match,
                "speaker_type": speaker_type,  # owner/known/unknown
                "predicted_speaker": predicted_speaker
            }
        except Exception as e:
            return {"error": str(e)}
