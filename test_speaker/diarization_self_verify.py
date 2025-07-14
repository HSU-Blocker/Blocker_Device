import os
import torch
from pydub import AudioSegment
from multiprocessing import Pool
import tempfile
from pyannote.audio import Pipeline, Inference
from pyannote.core import Segment
import torch.nn.functional as F

HF_TOKEN = os.getenv("HF_TOKEN")  # 환경변수에 Hugging Face Token 필요

'''
WAV 오디오 파일을 60초 단위로 분할하고

각 조각에 대해 **화자 분할(Speaker Diarization)**을 수행한 후

분할된 발화 구간을 기반으로 임베딩을 추출하고

가장 먼저 등장한 화자 구간을 기준(reference)으로 삼아

나머지 발화 구간들과의 유사도를 계산하여

각 화자가 기준 화자와 동일인인지 여부를 코사인 유사도 기반으로 분석.
'''

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
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=HF_TOKEN)
    result = pipeline(chunk_path)
    return [
        (chunk_path, turn.start + offset, turn.end + offset, speaker)
        for turn, _, speaker in result.itertracks(yield_label=True)
    ]

# 임베딩 추출 함수
def extract_embedding(model, audio_path, start, end):
    return model.crop(audio_path, Segment(start, end))  # torch.tensor([1, 192])

# 유사도 계산
def verify_speakers(ref_emb, test_emb):
    # numpy → tensor 변환
    if not isinstance(ref_emb, torch.Tensor):
        ref_emb = torch.tensor(ref_emb, dtype=torch.float32)
    if not isinstance(test_emb, torch.Tensor):
        test_emb = torch.tensor(test_emb, dtype=torch.float32)

    # (192,) → (1, 192) 로 reshape
    if ref_emb.ndim == 1:
        ref_emb = ref_emb.unsqueeze(0)
    if test_emb.ndim == 1:
        test_emb = test_emb.unsqueeze(0)

    similarity = F.cosine_similarity(ref_emb, test_emb, dim=1).item()
    return similarity


# 전체 실행
def process_with_self_reference(audio_file):
    print("GPU 사용 여부:", torch.cuda.is_available())

    # 1. 분할
    chunks = split_audio(audio_file, chunk_length_ms=60000)

    # 2. diarization
    with Pool(processes=min(os.cpu_count(), len(chunks))) as pool:
        diarization_results = pool.map(diarize_chunk, chunks)

    all_segments = [seg for chunk in diarization_results for seg in chunk]
    all_segments.sort(key=lambda x: x[1])  # 시작시간 기준 정렬

    if not all_segments:
        print("분할된 화자 구간이 없습니다.")
        return

    print("\n=== 화자 분할 결과 ===")
    for _, start, end, speaker in all_segments:
        print(f"{start:.1f}s ~ {end:.1f}s : Speaker {speaker}")

    # 3. 임베딩 모델 로드
    embedding_model = Inference("pyannote/embedding", window="whole")

    # 4. 첫 화자 세그먼트를 reference로 사용
    ref_path, ref_start, ref_end, ref_speaker = all_segments[0]
    print(f"\n🔎 기준 화자: Speaker {ref_speaker}, 구간: {ref_start:.1f}~{ref_end:.1f}s")

    ref_embedding = extract_embedding(embedding_model, ref_path, ref_start, ref_end)

    # 5. 나머지와 비교
    print("\n=== 유사도 비교 결과 (기준 화자와의 비교) ===")
    for chunk_path, start, end, speaker in all_segments:
        test_embedding = extract_embedding(embedding_model, chunk_path, start, end)
        similarity = verify_speakers(ref_embedding, test_embedding)

        print(f"[{start:.1f}s~{end:.1f}s] Speaker {speaker} → 유사도: {similarity:.4f}")


# 실행 진입점
if __name__ == "__main__":
    input_audio_path = "data/tfile.wav" # 분석할 입력 오디오 파일
    process_with_self_reference(input_audio_path)
