import os
import numpy as np
import torch
from pydub import AudioSegment
from multiprocessing import Pool
import tempfile
from pyannote.audio import Pipeline
from resemblyzer import VoiceEncoder, preprocess_wav
from collections import defaultdict

SAMPLE_RATE = 16000
HF_TOKEN = os.getenv("HF_TOKEN")

# 🔹 1. 오디오 분할
def split_audio(file_path, chunk_length_ms=60000):
    audio = AudioSegment.from_wav(file_path)
    chunk_paths = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunk_paths.append((chunk_path, i / 1000))  # 초 단위
    return chunk_paths, len(audio) / 1000

# 🔹 2. 병렬 diarization
def diarize_chunk(args):
    chunk_path, offset = args
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=HF_TOKEN)
    result = pipeline(chunk_path)
    return [
        (turn.start + offset, turn.end + offset, speaker)
        for turn, _, speaker in result.itertracks(yield_label=True)
    ]

# 🔹 3. 전체 흐름
def diarize_and_extract_embeddings(audio_path, save_path="data/reference_multi.npy"):
    print("GPU 사용 여부:", torch.cuda.is_available())

    # 1. 분할
    chunks, total_duration = split_audio(audio_path)

    # 2. 병렬 diarization 수행
    with Pool(processes=min(os.cpu_count(), len(chunks))) as pool:
        diarization_results = pool.map(diarize_chunk, chunks)

    # 3. 결과 정리
    all_segments = [seg for result in diarization_results for seg in result]
    all_segments.sort(key=lambda x: x[0])  # 시작 시간 기준

    print("\n=== 화자 분할 결과 ===")
    for start, end, speaker in all_segments:
        print(f"{start:.1f}s ~ {end:.1f}s : Speaker {speaker}")

    # 4. 화자별 음성 합치기
    speaker_segments = defaultdict(list)
    for start, end, speaker in all_segments:
        speaker_segments[speaker].append((start, end))

    audio = AudioSegment.from_wav(audio_path)
    encoder = VoiceEncoder()
    speaker_embeddings = {}

    for speaker, segments in speaker_segments.items():
        speaker_audio = AudioSegment.silent(duration=0)
        for start, end in segments:
            segment = audio[start * 1000:end * 1000]
            speaker_audio += segment

        samples = np.array(speaker_audio.get_array_of_samples()).astype(np.float32) / 32768.0
        if speaker_audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        embedding = encoder.embed_utterance(preprocess_wav(samples, SAMPLE_RATE))
        speaker_embeddings[speaker] = embedding
        print(f"✅ Speaker {speaker} 임베딩 추출 완료")

    # 5. 저장
    np.save(save_path, speaker_embeddings)
    print(f"\n💾 모든 화자 임베딩이 '{save_path}'에 저장되었습니다.")

# 🔹 실행
if __name__ == "__main__":
    diarize_and_extract_embeddings("data/tfile.wav")
