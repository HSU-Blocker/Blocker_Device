import os
import numpy as np
import torch
import sounddevice as sd
from scipy.io.wavfile import write
from resemblyzer import VoiceEncoder, preprocess_wav
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

# 설정
SAMPLE_RATE = 16000
RECORD_SECONDS = 5  # 녹음 시간 (초)
OUTPUT_DIR = "data/speakers_wav"
EMBEDDING_PATH = "data/reference_multi.npy"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def record_audio(filename: str):
    print(f"\n🎙️ '{filename}' 음성 녹음 시작 ({RECORD_SECONDS}초)...")
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()
    write(filename, SAMPLE_RATE, audio)
    print(f"✅ 녹음 완료: {filename}")

def register_speaker(speaker_name: str):
    encoder = VoiceEncoder()
    
    wav_path = os.path.join(OUTPUT_DIR, f"{speaker_name}.wav")
    record_audio(wav_path)
    
    # 오디오 로드 및 전처리
    audio = AudioSegment.from_wav(wav_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    preprocessed = preprocess_wav(samples, SAMPLE_RATE)
    embedding = encoder.embed_utterance(preprocessed)

    # 기존 임베딩 불러오기
    if os.path.exists(EMBEDDING_PATH):
        embeddings = np.load(EMBEDDING_PATH, allow_pickle=True).item()
    else:
        embeddings = {}

    # 저장
    embeddings[speaker_name] = embedding
    np.save(EMBEDDING_PATH, embeddings)
    print(f"💾 임베딩 저장 완료: '{speaker_name}' → {EMBEDDING_PATH}")

if __name__ == "__main__":
    speaker_name = input("\n등록할 화자 이름을 입력하세요: ").strip()
    if speaker_name:
        register_speaker(speaker_name)
    else:
        print("❗ 화자 이름이 입력되지 않았습니다.")
