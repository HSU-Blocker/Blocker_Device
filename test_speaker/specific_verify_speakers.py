import os
import numpy as np
import sounddevice as sd
from queue import Queue
from collections import deque
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine

# 설정
SAMPLE_RATE = 16000
FRAME_DURATION = 1  # 초 단위
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION)
WINDOW_DURATION = 3  # 누적 시간 (초)
WINDOW_SIZE = FRAME_SIZE * WINDOW_DURATION
SIMILARITY_THRESHOLD = 0.60
TARGET_SPEAKER = "SPEAKER_01"  # 비교 대상 화자

def verify_single_speaker(reference_embedding, test_embedding):
    similarity = 1 - cosine(reference_embedding, test_embedding)
    return similarity, similarity > SIMILARITY_THRESHOLD

def list_input_devices():
    print("\n🎙️ 사용 가능한 입력 장치 목록:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']} ({device['hostapi']})")

def run_verification_against_target(reference_embedding, target_name="Target"):
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
        buffer.extend(indata[:, 0])
        if len(buffer) == WINDOW_SIZE:
            q.put(np.array(buffer))

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=FRAME_SIZE, callback=callback):
        print(f"\n🎙️ 실시간 화자 검증 중 — 대상 화자: {target_name} (3초 누적)... (Ctrl+C로 종료)")
        try:
            while True:
                if not q.empty():
                    audio_data = q.get()
                    test_embedding = encoder.embed_utterance(preprocess_wav(audio_data, SAMPLE_RATE))
                    similarity, is_match = verify_single_speaker(reference_embedding, test_embedding)

                    if is_match:
                        print(f"✅ 동일 화자 ({target_name}) — 유사도: {similarity:.4f}")
                    else:
                        print(f"❌ 다른 화자 — 유사도: {similarity:.4f}")
        except KeyboardInterrupt:
            print("\n⏹️ 종료")

if __name__ == "__main__":
    all_embeddings = np.load("data/reference_multi.npy", allow_pickle=True).item()

    if TARGET_SPEAKER not in all_embeddings:
        print(f"[!] '{TARGET_SPEAKER}' 화자가 npy에 존재하지 않습니다.")
        print("🗂️ 등록된 화자 목록:")
        for name in all_embeddings:
            print(f" - {name}")
    else:
        print(f"\n🎯 비교 대상: {TARGET_SPEAKER}")
        target_embedding = all_embeddings[TARGET_SPEAKER]
        run_verification_against_target(target_embedding, target_name=TARGET_SPEAKER)
