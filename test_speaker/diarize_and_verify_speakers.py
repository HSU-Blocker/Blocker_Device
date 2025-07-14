import os
import time
import torch
from pydub import AudioSegment
from multiprocessing import Pool
import tempfile
from pyannote.audio import Pipeline
from pyannote.core import Segment
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine
import numpy as np

'''
화자 분할은 그대로 pyannote.audio의 Pipeline 사용.

임베딩 추출 및 유사도 계산은 Resemblyzer 사용 (VoiceEncoder.embed_utterance)

Segment 시간 범위를 이용해 해당 구간만 잘라 Resemblyzer에 전달.
'''

HF_TOKEN = os.getenv("HF_TOKEN")

# 오디오 분할 함수
def split_audio(file_path, chunk_length_ms=60000):
    audio = AudioSegment.from_wav(file_path)
    chunk_paths = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunk_paths.append((chunk_path, i / 1000))  # 초 단위 offset
    return chunk_paths

# diarization 수행 함수
def diarize_chunk(args):
    chunk_path, offset = args
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=HF_TOKEN)
    result = pipeline(chunk_path)
    return [
        (chunk_path, turn.start + offset, turn.end + offset, speaker)
        for turn, _, speaker in result.itertracks(yield_label=True)
    ]

# Resemblyzer 임베딩 추출 함수
def extract_embedding_resemblyzer(encoder, audio_path, start, end):
    # 1. 전체 오디오 불러오기
    audio = AudioSegment.from_wav(audio_path)

    # 2. 필요한 구간만 자르기 (ms 단위)
    segment_audio = audio[start * 1000 : end * 1000]

    # 3. 임시 파일로 저장
    temp_path = os.path.join(tempfile.gettempdir(), f"clip_{start:.2f}_{end:.2f}.wav")
    segment_audio.export(temp_path, format="wav")

    # 4. preprocess 및 임베딩 추출
    wav = preprocess_wav(temp_path)
    return encoder.embed_utterance(wav)

# 유사도 계산 (Resemblyzer는 cosine으로 계산)
def verify_speakers(reference_embedding, test_embedding):
    similarity = 1 - cosine(reference_embedding, test_embedding)
    return similarity

# 전체 실행
def process_with_self_reference(audio_file):
    print("GPU 사용 여부:", torch.cuda.is_available())
    total_start = time.time()  # 전체 시간 측정 시작

    # 1. 오디오 분할
    start = time.time()
    chunks = split_audio(audio_file, chunk_length_ms=60000)
    print(f"🧩 오디오 분할 완료 - 소요 시간: {time.time() - start:.2f}초")

    # 2. diarization
    start = time.time()
    with Pool(processes=min(os.cpu_count(), len(chunks))) as pool:
        diarization_results = pool.map(diarize_chunk, chunks)
    print(f"🔊 화자 분할 완료 - 소요 시간: {time.time() - start:.2f}초")

    all_segments = [seg for chunk in diarization_results for seg in chunk]
    all_segments.sort(key=lambda x: x[1])

    if not all_segments:
        print("분할된 화자 구간이 없습니다.")
        return

    print("\n=== 화자 분할 결과 ===")
    for _, start_time, end_time, speaker in all_segments:
        print(f"{start_time:.1f}s ~ {end_time:.1f}s : Speaker {speaker}")

    # 3. Resemblyzer 임베딩 모델 로드
    encoder = VoiceEncoder()

    # 4. 기준 화자 세그먼트 설정
    ref_path, ref_start, ref_end, ref_speaker = all_segments[0]
    print(f"\n🔎 기준 화자: Speaker {ref_speaker}, 구간: {ref_start:.1f}~{ref_end:.1f}s")

    start = time.time()
    reference_embedding = extract_embedding_resemblyzer(encoder, ref_path, ref_start, ref_end)
    print(f"🎙️ 기준 화자 임베딩 완료 - 소요 시간: {time.time() - start:.2f}초")

    # 5. 다른 화자들과 비교
    print("\n=== 유사도 비교 결과 (기준 화자와의 비교) ===")
    start = time.time()
    for chunk_path, start_time, end_time, speaker in all_segments:
        test_embedding = extract_embedding_resemblyzer(encoder, chunk_path, start_time, end_time)
        similarity = verify_speakers(reference_embedding, test_embedding)
        print(f"[{start_time:.1f}s~{end_time:.1f}s] Speaker {speaker} → 유사도: {similarity:.4f}")

        if similarity >= 0.75:
            print("  ✅ 동일 화자로 추정됨")
        else:
            print("  ❌ 다른 화자로 추정됨")
    print(f"🧠 화자 비교 완료 - 소요 시간: {time.time() - start:.2f}초")

    print(f"\n⏱️ 전체 처리 시간: {time.time() - total_start:.2f}초")

# 실행 진입점
if __name__ == "__main__":
    input_audio_path = "data/tfile.wav"  # 분석할 입력 오디오 파일
    process_with_self_reference(input_audio_path)
