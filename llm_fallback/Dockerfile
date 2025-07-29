FROM python:3.10-slim

WORKDIR /app

# 변수 정의
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY . .


RUN echo "TOKEN is: $HF_TOKEN"  

RUN pip install flask transformers torch

EXPOSE 5000
CMD ["python", "app.py"]
