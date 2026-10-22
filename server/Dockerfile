FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r server/requirements.txt

COPY server/app server/app
COPY research research

RUN useradd --create-home --uid 10001 flowsync \
    && mkdir -p /app/server/models /app/server/data \
    && chown -R flowsync:flowsync /app

USER flowsync
WORKDIR /app/server
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
