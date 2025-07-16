FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc
RUN pip install requests rasa==3.5.10 rasa-sdk==3.5.0 transformers torch==2.1.0+cpu -f https://download.pytorch.org/whl/torch_stable.html

WORKDIR /app
COPY . /app

EXPOSE 5055
CMD ["rasa", "run", "actions", "--actions", "actions"]
