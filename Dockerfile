FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-dev.txt ./
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels \
    -r requirements.txt -r requirements-dev.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --shell /bin/bash app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
COPY --chown=app:app . .
RUN chmod +x entrypoint.sh
USER app
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
