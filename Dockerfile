# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /app/.venv
COPY requirements.txt .
RUN /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN useradd --create-home appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "app:create_app()"
