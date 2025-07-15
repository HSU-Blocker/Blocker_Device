from faster_whisper import WhisperModel
import torchaudio
import tempfile
import subprocess
import os

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

def webm_bytes_to_tensor_waveform(audio_bytes, sample_rate=16000):
    """
    webm bytes를 입력받아 STT용 waveform(torch.Tensor, 16kHz, (1, N))으로 변환
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        # ffmpeg로 webm → wav 변환 후 로드
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_path, "-ar", str(sample_rate), "-ac", "1", tmp_wav_path
        ], check=True)
        waveform, sr = torchaudio.load(tmp_wav_path)
        os.remove(tmp_wav_path)
    finally:
        os.remove(tmp_path)
    if sr != sample_rate:
        waveform = torchaudio.functional.resample(waveform, sr, sample_rate)
    return waveform
