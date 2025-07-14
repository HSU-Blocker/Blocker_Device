# from TTS.api import TTS as CoquiTTS  # Coqui TTS 사용 코드 주석처리
import io
# import soundfile as sf  # Coqui TTS용 사운드파일 주석처리
from google.cloud import texttospeech

class TTS:
    def __init__(self, default_lang="ko"):
        self.default_lang = default_lang
        self.client = texttospeech.TextToSpeechClient()

    def synthesize(self, text: str, language=None) -> bytes:
        lang = language or self.default_lang
        # 언어별 기본 voice 설정 (필요시 확장)
        voice_map = {
            "ko": "ko-KR-Standard-A",
            "en": "en-US-Standard-C",
            "ja": "ja-JP-Standard-A",
            "fr": "fr-FR-Standard-A",
            "zh": "cmn-CN-Standard-A",
            "es": "es-ES-Standard-A",
        }
        voice_name = voice_map.get(lang, "ko-KR-Standard-A")
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_name[:5], name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content

    # 아래는 Coqui TTS용 코드 (참고용, 비활성화)
    # LANGUAGE_MODEL_MAP = {
    #     "ko": "tts_models/ko/kss/tacotron2-DDC",
    #     "en": "tts_models/en/ljspeech/tacotron2-DDC",
    #     "ja": "tts_models/ja/kokoro/tacotron2-DDC",
    #     "fr": "tts_models/fr/mai/tacotron2-DDC",
    #     "zh": "tts_models/zh-CN/baker/tacotron2-DDC",
    #     "zh-CN": "tts_models/zh-CN/baker/tacotron2-DDC",
    #     "es": "tts_models/es/mai/tacotron2-DDC",
    #     # 필요시 추가 지원 언어 및 모델 경로를 여기에 추가
    # }
    # DEFAULT_MODEL = "tts_models/ko/kss/tacotron2-DDC"
    # DEFAULT_LANG = "ko"
    # def get_model(self, lang):
    #     # 언어코드가 정확히 없으면, 앞 2글자만 추출해서 fallback
    #     model_name = self.LANGUAGE_MODEL_MAP.get(lang)
    #     if not model_name and lang:
    #         short_lang = lang.split("-")[0]
    #         model_name = self.LANGUAGE_MODEL_MAP.get(short_lang, self.DEFAULT_MODEL)
    #     if model_name not in self.models:
    #         self.models[model_name] = CoquiTTS(model_name)
    #     return self.models[model_name]
    #
    # def synthesize(self, text: str, language=None) -> bytes:
    #     lang = language or self.default_lang
    #     tts_model = self.get_model(lang)
    #     wav = tts_model.tts(text=text)
    #     buf = io.BytesIO()
    #     sf.write(buf, wav, tts_model.synthesizer.output_sample_rate, format='WAV')
    #     return buf.getvalue()
