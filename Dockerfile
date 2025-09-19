# 플랫폼 지정 및 Python 3.10-slim 이미지 사용
FROM --platform=linux/arm64 python:3.10-slim

# APT 다운로드 문제 방지용 설정 추가 + 기본 패키지 설치
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99custom && \
    apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libgmp-dev \
        libssl-dev \
        wget \
        cmake \
        flex \
        bison \
        autoconf \
        libtool \
        python3-dev \
        openssl \
        ffmpeg \
        libsndfile1 \
        portaudio19-dev \
        libasound2-dev \
        alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# PBC 라이브러리 설치
RUN wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz && \
    tar -xvf pbc-0.5.14.tar.gz && \
    cd pbc-0.5.14 && \
    ./configure --disable-gmp-tests && \
    make && \
    make install && \
    ldconfig && \
    cd .. && \
    rm -rf pbc-0.5.14 pbc-0.5.14.tar.gz

# PyParsing 및 Hypothesis 설치
RUN pip install --no-cache-dir pyparsing==2.4.7 hypothesis

# charm-crypto 설치
RUN git clone https://github.com/JHUISI/charm.git && \
    cd charm && \
    ./configure.sh && \
    make && \
    make install && \
    ldconfig && \
    cd .. && \
    rm -rf charm

# 필요한 디렉토리 생성
RUN mkdir -p /app/client/keys /app/client/updates

# 요구사항 파일 복사 및 최적화된 설치
COPY requirements.txt .

# 먼저 pip 업그레이드 및 기본 패키지
RUN pip install --upgrade pip wheel

# CPU 버전의 PyTorch 먼저 설치 (더 빠르고 안정적)
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.1.0 \
    torchaudio==2.1.0

# Whisper base 모델을 미리 다운로드하여 캐시에 저장
RUN pip install faster-whisper && \
    python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Coqui TTS 및 관련 패키지 설치 주석처리
# RUN pip install TTS==0.21.3

# 나머지 패키지들을 재시도 옵션과 함께 설치
RUN pip install \
    regex>=2022.3.15 \
    pycryptodome>=3.14.1 \
    cryptography>=36.0.0 \
    --no-cache-dir -r requirements.txt

# huggingface_hub 설치 (huggingface-cli 포함됨)
RUN pip install --no-cache-dir huggingface_hub

# 필요한 추가 패키지 설치
RUN pip install pycryptodome>=3.14.1 cryptography>=36.0.0

# 프로젝트 파일 복사
COPY . .

# # Google Cloud 서비스 계정 키 복사 (파일명은 실제 파일명에 맞게 수정)
# COPY electric-vision-465910-b0-fd08e1f02d86.json /app/your-service-account-file.json

# Flask 앱 실행
EXPOSE 5050
CMD ["python", "backend/api.py"]
