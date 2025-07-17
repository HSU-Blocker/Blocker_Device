FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install flask transformers torch

EXPOSE 5000
CMD ["python", "app.py"]
