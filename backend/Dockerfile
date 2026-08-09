FROM python:3.13.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip==26.0.1 \
    && /opt/venv/bin/pip install .

FROM python:3.13.11-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system postx \
    && useradd --system --gid postx --home-dir /app --shell /usr/sbin/nologin postx

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN chown -R postx:postx /app

USER postx
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
