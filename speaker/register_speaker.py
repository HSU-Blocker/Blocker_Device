import os
import io
import numpy as np
import torchaudio
import sounddevice as sd
from scipy.io.wavfile import write
from resemblyzer import VoiceEncoder, preprocess_wav
from pydub import AudioSegment
from dotenv import load_dotenv
import logging

load_dotenv()

# 설정
SAMPLE_RATE = 16000
RECORD_SECONDS = 5  # 녹음 시간 (초)
OUTPUT_DIR = "data/speakers_wav"
EMBEDDING_PATH = "data/reference_multi.npy"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def register_speaker_from_waveform(speaker_name: str, waveform: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """
    waveform(float32 np.ndarray)와 speaker_name을 받아 임베딩을 저장
    """
    encoder = VoiceEncoder()
    logging.info(f"화자 등록: {speaker_name} ({waveform.shape})")
    preprocessed = preprocess_wav(waveform, sample_rate)
    embedding = encoder.embed_utterance(preprocessed)

    # 기존 임베딩 불러오기
    if os.path.exists(EMBEDDING_PATH):
        embeddings = np.load(EMBEDDING_PATH, allow_pickle=True).item()
    else:
        embeddings = {}

    embeddings[speaker_name] = embedding
    np.save(EMBEDDING_PATH, embeddings)
    logging.info(f"💾 임베딩 저장 완료: '{speaker_name}' → {EMBEDDING_PATH}")
    logging.info(f"[임베딩 등록 현황] 현재 등록된 화자: {list(embeddings.keys())}")
    return True, speaker_name

def webm_bytes_to_numpy_waveform(webm_bytes, sample_rate=16000):
    """
    webm bytes를 화자 등록/인식용 numpy waveform(float32, mono, sample_rate)로 변환
    """    
    # WebM → PCM 변환
    audio = AudioSegment.from_file(io.BytesIO(webm_bytes), format="webm")
    
    # mono + 원하는 sample_rate 변환
    audio = audio.set_channels(1).set_frame_rate(sample_rate)

    # numpy waveform 변환
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / (1 << 15)
    return samples


## 테스트용
def register_speaker(speaker_name: str):
    encoder = VoiceEncoder()
    
    wav_path = os.path.join(OUTPUT_DIR, f"{speaker_name}.wav")
    
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
