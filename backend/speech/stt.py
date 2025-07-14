from faster_whisper import WhisperModel
import torchaudio
import tempfile
import torch
import subprocess
import os
import io

class WhisperSTT:
    def __init__(self, initial_prompt=None, model_size="base"):  # tiny, base, small 등 선택 가능
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"
        )
        self.initial_prompt = initial_prompt

    def transcribe(self, waveform):
        # 원문 그대로 텍스트 추출 (task="transcribe")
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            torchaudio.save(f.name, waveform, 16000)
            segments, info = self.model.transcribe(
                f.name,
                task="transcribe",
                initial_prompt=self.initial_prompt
            )

        text = "".join([segment.text for segment in segments])
        self.last_detected_language = getattr(info, "language", None)
        return text.strip()

    def translate_to_english(self, waveform):
        # 영어 번역 (task="translate")
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            torchaudio.save(f.name, waveform, 16000)
            segments, info = self.model.transcribe(
                f.name,
                task="translate",
                initial_prompt=self.initial_prompt
            )

        text = "".join([segment.text for segment in segments])
        self.last_detected_language = getattr(info, "language", None)
        return text.strip()

def load_audio(input_path):
    """
    다양한 오디오 포맷(webm, wav 등)을 16kHz waveform으로 변환하여 반환
    """
    if input_path.endswith(".webm"):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", tmp_wav_path
        ], check=True)
        waveform, sr = torchaudio.load(tmp_wav_path)
        os.remove(tmp_wav_path)
    else:
        with open(input_path, "rb") as f:
            audio_bytes = f.read()
        waveform, sr = torchaudio.load(io.BytesIO(audio_bytes))
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, sr, 16000)
    return waveform
