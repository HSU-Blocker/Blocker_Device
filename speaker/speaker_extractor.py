import os
import numpy as np
import torch
from pydub import AudioSegment
from pyannote.audio import Pipeline
from resemblyzer import VoiceEncoder, preprocess_wav
from collections import defaultdict

# 설정
AUDIO_PATH = "data/tfile.wav"
OUTPUT_DIR = "data/speakers_wav"
EMBEDDING_PATH = "data/reference_multi.npy"
HF_TOKEN = os.getenv("HF_TOKEN")
SAMPLE_RATE = 16000

# 디렉토리 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)

# GPU 사용 여부 출력
print("GPU 사용 여부:", torch.cuda.is_available())

# 원본 오디오 로드
audio = AudioSegment.from_wav(AUDIO_PATH)

# diarization 수행
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=HF_TOKEN)
diarization = pipeline(AUDIO_PATH)

# 화자별 구간 정리
speaker_segments = defaultdict(list)
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speaker_segments[speaker].append((turn.start, turn.end))

# resemblyzer 인코더 초기화
encoder = VoiceEncoder()
speaker_embeddings = {}

# 기존 임베딩 불러오기 (누적 저장용)
if os.path.exists(EMBEDDING_PATH):
    previous_embeddings = np.load(EMBEDDING_PATH, allow_pickle=True).item()
else:
    previous_embeddings = {}

# 고유 speaker index 계산
existing_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("speaker_") and f.endswith(".wav")]
existing_indices = [int(f.split("_")[1].split(".")[0]) for f in existing_files if f.split("_")[1].split(".")[0].isdigit()]
base_index = max(existing_indices, default=-1) + 1

# 화자별 오디오 생성 및 임베딩 저장
for i, (speaker, segments) in enumerate(speaker_segments.items()):
    new_speaker_index = base_index + i
    print(f"\nSpeaker {new_speaker_index} 오디오 처리 중...")
    samples_all = []

    for start, end in segments:
        segment = audio[start * 1000:end * 1000]
        samples = np.array(segment.get_array_of_samples()).astype(np.float32) / 32768.0
        if segment.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)
        samples_all.append(samples)

    full_samples = np.concatenate(samples_all)
    preprocessed = preprocess_wav(full_samples, SAMPLE_RATE)
    embedding = encoder.embed_utterance(preprocessed)

    speaker_key = f"speaker_{new_speaker_index}"
    speaker_embeddings[speaker_key] = embedding
    print(f"임베딩 생성 완료: {speaker_key}")

    # 오디오 파일 저장
    speaker_audio = AudioSegment.silent(duration=0)
    for start, end in segments:
        speaker_audio += audio[start * 1000:end * 1000]
    out_path = os.path.join(OUTPUT_DIR, f"{speaker_key}.wav")
    speaker_audio.export(out_path, format="wav")
    print(f"저장 완료: {out_path}")

# 임베딩 누적 저장
previous_embeddings.update(speaker_embeddings)
np.save(EMBEDDING_PATH, previous_embeddings)
print(f"\n모든 화자 임베딩이 누적 저장되었습니다 → '{EMBEDDING_PATH}'")
