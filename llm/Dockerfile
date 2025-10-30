FROM rasa/rasa:3.6.2

USER root
WORKDIR /app

COPY . /app
RUN rm -rf /app/.rasa/cache /app/.rasa/tmp /app/.rasa/models || true
RUN chmod -R 777 /app

USER 1001
EXPOSE 5005

# Rasa 기본 entrypoint를 무시
ENTRYPOINT []

# 학습 및 실행은 docker-compose에서 수행
CMD ["/bin/bash", "-c", "chmod -R 777 /app && rasa train && rasa run --enable-api --port 5005 --debug"]
