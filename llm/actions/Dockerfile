FROM --platform=linux/arm64 python:3.8-slim

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install \
        tensorflow==2.11.0 \
        tensorflow-addons==0.19.0 && \
    pip install \
        requests \
        rasa==3.5.10 \
        rasa-sdk==3.5.0 \
        transformers \
        torch==2.1.0 \
        --extra-index-url https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY . /app

EXPOSE 5055
CMD ["rasa", "run", "actions", "--actions", "actions"]
