import os
import numpy as np
import torch
import sounddevice as sd
from queue import Queue
from collections import deque
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine


SAMPLE_RATE = 16000
FRAME_DURATION = 1  # 초 단위
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION)
WINDOW_DURATION = 3  # 누적 시간 (초)
WINDOW_SIZE = FRAME_SIZE * WINDOW_DURATION
SIMILARITY_THRESHOLD = 0.60

def verify_speakers_from_waveform(np_waveform, embedding_path="data/reference_multi.npy"):
    """
    webm/wav 등에서 추출한 numpy waveform(np_waveform)을 받아 등록된 화자와 비교하여
    (best_name, best_similarity, is_match) 반환
    """
    # 1. 임베딩 DB 로드
    reference_embeddings = np.load(embedding_path, allow_pickle=True).item()
    # 2. 입력 waveform 임베딩 추출
    encoder = VoiceEncoder()
    test_embedding = encoder.embed_utterance(preprocess_wav(np_waveform, SAMPLE_RATE))
    # 3. 유사도 계산 후 가장 유사도가 높은 화자 이름, 유사도, 일치 여부 반환
    results = []
    for name, ref_emb in reference_embeddings.items():
        similarity = 1 - cosine(ref_emb, test_embedding)
        results.append((name, similarity))
    results.sort(key=lambda x: x[1], reverse=True)
    best_name, best_similarity = results[0]
    is_match = best_similarity > SIMILARITY_THRESHOLD
    return best_name, best_similarity, is_match


## 테스트용
def verify_speakers(reference_embeddings, test_embedding):
    results = []
    for name, ref_emb in reference_embeddings.items():
        similarity = 1 - cosine(ref_emb, test_embedding)
        results.append((name, similarity))
    results.sort(key=lambda x: x[1], reverse=True)
    best_name, best_similarity = results[0]
    return best_name, best_similarity, best_similarity > SIMILARITY_THRESHOLD

def list_input_devices():
    print("\n🎙️ 사용 가능한 입력 장치 목록:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']} ({device['hostapi']})")

def run_streaming_verification(reference_embeddings):
    encoder = VoiceEncoder()
    q = Queue()
    buffer = deque(maxlen=WINDOW_SIZE)

    list_input_devices()

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        print("\n[!] 입력 장치가 설정되어 있지 않습니다.")
        return
    else:
        print(f"\n🎧 기본 입력 장치 ID: {default_input} — {sd.query_devices(default_input)['name']}")

    def callback(indata, frames, time, status):
        if status:
            print(f"[!] 마이크 상태 경고: {status}")
        buffer.extend(indata[:, 0])  # mono 기준
        if len(buffer) == WINDOW_SIZE:
            q.put(np.array(buffer))

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=FRAME_SIZE, callback=callback):
        print("\n 실시간 화자 검증 중 (3초 누적 기준)... (Ctrl+C로 종료)")
        try:
            while True:
                if not q.empty():
                    audio_data = q.get()
                    test_embedding = encoder.embed_utterance(preprocess_wav(audio_data, SAMPLE_RATE))

                    best_name, best_similarity, is_match = verify_speakers(reference_embeddings, test_embedding)
                    if is_match:
                        print(f"✅ 동일 화자 식별됨: '{best_name}' (유사도: {best_similarity:.4f})")
                        return True, best_name
                    else:
                        print(f"❌ 등록된 화자와 일치하지 않음 — 최고 유사도: {best_similarity:.4f} (예상 화자: {best_name})")
                        return False, best_name
        except KeyboardInterrupt:
            print("\n 종료")

if __name__ == "__main__":
    reference_embeddings = np.load("data/reference_multi.npy", allow_pickle=True).item()
    print("\n📁 등록된 화자 목록:")
    for name in reference_embeddings:
        print(f" - {name}")
    run_streaming_verification(reference_embeddings)