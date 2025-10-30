import os
import tempfile
import subprocess
from faster_whisper import WhisperModel


class WhisperSTT:
    """
    Whisper 기반 STT + 번역 통합 클래스
    - WebM/Opus 입력을 ffmpeg로 WAV(PCM16) 변환
    - Whisper에서 STT(한국어)와 영어 번역을 각각 수행
    """

    def __init__(self, initial_prompt=None, model_size="base"):
        self.model = WhisperModel(
            model_size,
            device="cpu",              # GPU 사용 시 "cuda"
            compute_type="float32"     # float16은 ARM/CPU에서 에러 발생 가능
        )
        self.initial_prompt = initial_prompt
        self.last_detected_language = None

    def transcribe(self, audio_path):
        """원문(한국어 등)을 Whisper로 인식"""
        segments, info = self.model.transcribe(
            audio_path,
            task="transcribe",  # 원문 그대로 인식
            initial_prompt=self.initial_prompt
        )
        text = "".join([seg.text for seg in segments]).strip()
        self.last_detected_language = getattr(info, "language", None)
        return text

    def translate_to_english(self, audio_path):
        """Whisper를 사용해 영어 번역 결과 생성"""
        segments, _ = self.model.transcribe(
            audio_path,
            task="translate",  # 영어로 번역
            initial_prompt=self.initial_prompt
        )
        return "".join([seg.text for seg in segments]).strip()

    def process_audio(self, audio_bytes, sample_rate=16000):
        """
        WebM/Opus/WAV bytes를 받아:
        1️⃣ ffmpeg로 PCM WAV 변환
        2️⃣ Whisper로 STT(원문) 및 번역 수행
        3️⃣ 결과 반환
        """
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            input_path = tmp_in.name

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
                output_path = tmp_out.name

            # ffmpeg 변환 (WebM → PCM WAV)
            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_path,
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", str(sample_rate),
                output_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # STT (원문)
            transcribed_text = self.transcribe(output_path)

            # 번역 (영어)
            translated_text = self.translate_to_english(output_path)

            return {
                "transcribed_text": transcribed_text,
                "translated_text": translated_text,
                "detected_lang": self.last_detected_language
            }

        except subprocess.CalledProcessError as e:
            return {"error": f"ffmpeg 변환 실패: {e}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            # 임시 파일 정리
            if os.path.exists(input_path):
                os.remove(input_path)
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
