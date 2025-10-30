FROM python:3.8-slim

WORKDIR /app

# 변수 정의
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY . .

# PyTorch 전용 인덱스로 torch 관련 패키지 설치
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.1.0 \
    torchvision==0.16.0 \
    torchaudio==2.1.0

# 기본 PyPI 인덱스로 일반 패키지 설치
RUN echo "TOKEN is: $HF_TOKEN"  

RUN pip install flask transformers torch

EXPOSE 5000
CMD ["python", "app.py"]