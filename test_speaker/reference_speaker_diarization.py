import os
import numpy as np
from pydub import AudioSegment
from pyannote.audio import Pipeline
from collections import defaultdict

AUDIO_PATH = "data/tfile.wav"
OUTPUT_DIR = "data/speakers_wav"
HF_TOKEN = os.getenv("HF_TOKEN")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 원본 오디오 로드
audio = AudioSegment.from_wav(AUDIO_PATH)

# pyannote로 diarization 수행
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=HF_TOKEN)
diarization = pipeline(AUDIO_PATH)

# 화자별 구간 정리
speaker_segments = defaultdict(list)
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speaker_segments[speaker].append((turn.start, turn.end))

# 화자별 음성 저장
for speaker, segments in speaker_segments.items():
    speaker_audio = AudioSegment.silent(duration=0)
    for start, end in segments:
        segment = audio[start * 1000:end * 1000]
        speaker_audio += segment

    export_path = os.path.join(OUTPUT_DIR, f"{speaker}.wav")
    speaker_audio.export(export_path, format="wav")
    print(f"✅ 저장 완료: {export_path}")
