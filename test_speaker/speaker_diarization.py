import os
import torch
from pydub import AudioSegment
from multiprocessing import Pool  # multiprocessing으로 변경
import tempfile
from pyannote.audio import Pipeline

# ==========================
# 1. 오디오 분할 함수
# ==========================
def split_audio(file_path, chunk_length_ms=60000):  # 60초로 분할
    audio = AudioSegment.from_wav(file_path)
    chunk_paths = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunk_paths.append((chunk_path, i / 1000))  # 시작 시간 (초)
    return chunk_paths

# ==========================
# 2. 병렬 diarization 실행 함수
# (multiprocessing-safe 구조)
# ==========================
def diarize_chunk(args):
    chunk_path, offset = args

    # 각 프로세스에서 개별 Pipeline 로딩 (fork-safe)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=os.getenv("HF_TOKEN")
    )

    result = pipeline(chunk_path)

    # 결과에 offset 적용
    return [
        (turn.start + offset, turn.end + offset, speaker)
        for turn, _, speaker in result.itertracks(yield_label=True)
    ]

# ==========================
# 3. 전체 흐름
# ==========================
if __name__ == "__main__":
    original_file = "data/tfile.wav"

    print("GPU 사용 여부:", torch.cuda.is_available())

    # 1. 오디오 분할
    chunks = split_audio(original_file, chunk_length_ms=60000)

    # 2. 병렬 처리 (multiprocessing 기반)
    with Pool(processes=min(os.cpu_count(), len(chunks))) as pool:
        diarization_results = pool.map(diarize_chunk, chunks)

    # 3. 결과 정렬 및 출력
    all_segments = [seg for result in diarization_results for seg in result]
    all_segments.sort(key=lambda x: x[0])  # 시작 시간 기준 정렬

    print("\n=== 화자 분할 결과 ===")
    for start, end, speaker in all_segments:
        print(f"{start:.1f}s ~ {end:.1f}s : Speaker {speaker}")


# from pyannote.audio import Pipeline
# import os

# # Hugging Face 토큰을 환경변수에서 불러와 인증
# pipeline = Pipeline.from_pretrained(
#     "pyannote/speaker-diarization",
#     use_auth_token=os.getenv("HF_TOKEN")
# )

# diarization = pipeline("data/tfile.wav")

# for turn, _, speaker in diarization.itertracks(yield_label=True):
#     print(f"{turn.start:.1f}s ~ {turn.end:.1f}s : Speaker {speaker}")