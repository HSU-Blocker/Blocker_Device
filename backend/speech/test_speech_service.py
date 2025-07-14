from pipeline import SpeechService
from stt import WhisperSTT
from tts import TTS
from translator import TranslatorModule
import torchaudio

# sample_korean.wav는 '헤이 블로커, 업데이트해줘'라는 음성입니다.

def test_full_pipeline():
    with open("sample_chinese.wav", "rb") as f:
        audio_bytes = f.read()

    # VAD 생략: 바로 waveform 변환
    import io
    waveform, sr = torchaudio.load(io.BytesIO(audio_bytes))
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, sr, 16000)

    # Whisper STT
    stt = WhisperSTT(
        initial_prompt=(
            "‘헤이 블로커’는 항상 음성의 첫 부분에 등장하며, 'Hey Blocker'로 인식되어야 합니다."
        )
    )
    stt_text = stt.translate(waveform)
    detected_lang = getattr(stt, 'last_detected_language', None)
    print("[STT+번역] 결과:", stt_text)
    print("[감지된 언어]", detected_lang)

    # 3. 웨이크워드 제거 (문장 내 포함 여부로)
    # wakeword_remover = WakeWordRemover()
    # text_wo_wakeword = wakeword_remover.remove(stt_text)
    # print("[웨이크워드 제거 후 텍스트] 결과:", text_wo_wakeword)
    # if ("hey blocker" in stt_text.lower()) and ("hey blocker" not in text_wo_wakeword.lower()):
    #     print("[PASS] 웨이크워드가 정상적으로 제거되었습니다.")
    # else:
    #     print("[FAIL] 웨이크워드 제거 결과가 예상과 다릅니다.")

    # 4. TTS 변환 (영어 텍스트를 Whisper가 감지한 언어로 번역 후 음성 변환)
    translator = TranslatorModule()
    target_lang = detected_lang or 'ko'
    tts_input_text = translator.translate(stt_text, dest=target_lang)
    print(f"[TTS 변환용 텍스트] ({target_lang}):", tts_input_text)

    tts = TTS()
    tts_audio = tts.synthesize(tts_input_text, language=target_lang)
    output_path = "/app/backend/speech/output.wav"
    with open(output_path, "wb") as f:
        f.write(tts_audio)
    print(f"[TTS] {output_path} 저장됨 (컨테이너 경로, 로컬 볼륨 연결 시 동기화)")

if __name__ == "__main__":
    test_full_pipeline()
