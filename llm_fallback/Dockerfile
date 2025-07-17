FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY . .

# PyTorch 전용 인덱스로 torch 관련 패키지 설치
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
    torch==2.1.0 \
    torchvision==0.16.0 \
    torchaudio==2.1.0

# 기본 PyPI 인덱스로 일반 패키지 설치
RUN pip install flask transformers

EXPOSE 5000
CMD ["python", "app.py"]
