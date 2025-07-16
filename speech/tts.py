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
