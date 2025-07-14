from stt import WhisperSTT, load_audio
from tts import TTS
from translator import TranslatorModule

class SpeechService:
    def __init__(self, initial_prompt=None):
        self.stt = WhisperSTT(initial_prompt=initial_prompt)
        self.tts = TTS()
        self.translator = TranslatorModule()

    def process_audio(self, audio_bytes_or_path):
        """
        webm/wav 등을 받아서 waveform 변환
        원문(STT), 영어 번역, 언어감지 결과 반환
        """
        if isinstance(audio_bytes_or_path, (bytes, bytearray)):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes_or_path)
                tmp_path = tmp.name
            try:
                waveform = load_audio(tmp_path)
            finally:
                import os
                os.remove(tmp_path)
        else:
            waveform = load_audio(audio_bytes_or_path)
        transcribed_text = self.stt.transcribe(waveform)
        translated_text = self.stt.translate_to_english(waveform)
        detected_lang = getattr(self.stt, 'last_detected_language', None)
        return {
            'transcribed_text': transcribed_text,
            'translated_text': translated_text,
            'detected_lang': detected_lang
        }

    def get_transcription(self, audio_bytes_or_path):
        result = self.process_audio(audio_bytes_or_path)
        return {
            'transcribed_text': result['transcribed_text'],
            'detected_lang': result['detected_lang']
        }

    def get_translation(self, audio_bytes_or_path):
        result = self.process_audio(audio_bytes_or_path)
        return {
            'translated_text': result['translated_text'],
            'detected_lang': result['detected_lang']
        }

    def text_to_audio(self, text, target_language=None, translate=False):
        # translate=True면 text를 target_language로 번역 후 음성합성
        if translate and target_language:
            text = self.translator.translate(text, dest=target_language)
        return self.tts.synthesize(text, language=target_language)
