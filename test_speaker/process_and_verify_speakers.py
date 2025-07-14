import os
import torch
from pydub import AudioSegment
from multiprocessing import Pool
import tempfile
from pyannote.audio import Pipeline, Inference
from pyannote.core import Segment
import torch.nn.functional as F

# 오디오 분할 함수
def split_audio(file_path, chunk_length_ms=60000):
    audio = AudioSegment.from_wav(file_path)
    chunk_paths = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunk_paths.append((chunk_path, i / 1000))  # 초 단위 시작 시간
    return chunk_paths

# 병렬 diarization 함수
def diarize_chunk(args):
    chunk_path, offset = args
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.getenv("HF_TOKEN"))
    result = pipeline(chunk_path)
    return [
        (chunk_path, turn.start + offset, turn.end + offset, speaker)
        for turn, _, speaker in result.itertracks(yield_label=True)
    ]

# 임베딩 추출 함수
def extract_embedding(audio_path, start, end):
    embedding_model = Inference("pyannote/embedding", window="whole")
    segment = Segment(start, end)
    return embedding_model.crop(audio_path, segment)  # torch.tensor of shape [1, 192]

# 화자 유사도 비교 함수
def verify_speakers(reference_embedding, test_embedding, threshold=0.75):
    similarity = F.cosine_similarity(reference_embedding, test_embedding).item()
    return similarity, similarity > threshold

# 메인 처리 함수
def process_and_verify_speakers(audio_file, reference_db):
    """
    audio_file: 입력 오디오 파일 (WAV)
    reference_db: {"Alice": ("alice.wav", 0.0, 3.0)} 형태의 화자 참조 임베딩 정보
    """
    print("GPU 사용 여부:", torch.cuda.is_available())

    # Step 1. 오디오 분할
    chunks = split_audio(audio_file, chunk_length_ms=60000)

    # Step 2. 화자 분할
    with Pool(processes=min(os.cpu_count(), len(chunks))) as pool:
        diarization_results = pool.map(diarize_chunk, chunks)

    all_segments = [seg for chunk in diarization_results for seg in chunk]
    all_segments.sort(key=lambda x: x[1])  # 시작 시간 기준 정렬

    print("\n=== 화자 분할 결과 ===")
    for _, start, end, speaker in all_segments:
        print(f"{start:.1f}s ~ {end:.1f}s : Speaker {speaker}")

    # Step 3. 화자 식별 (임베딩 비교)
    print("\n=== 화자 검증 결과 ===")
    embedding_model = Inference("pyannote/embedding", window="whole")

    for chunk_path, start, end, speaker in all_segments:
        test_embedding = embedding_model.crop(chunk_path, Segment(start, end))

        for name, (ref_path, ref_start, ref_end) in reference_db.items():
            ref_embedding = embedding_model.crop(ref_path, Segment(ref_start, ref_end))
            similarity, matched = verify_speakers(ref_embedding, test_embedding)

            if matched:
                print(f"[{start:.1f}s~{end:.1f}s] Speaker {speaker} ≈ {name} ✅ (유사도: {similarity:.4f})")
                break
        else:
            print(f"[{start:.1f}s~{end:.1f}s] Speaker {speaker} ❌ (일치하는 화자 없음)")

