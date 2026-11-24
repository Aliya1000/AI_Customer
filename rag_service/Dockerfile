# ==============================================================================
# Standalone RAG Microservice Dockerfile (Port 8001)
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY rag_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/rag_service/data && \
    chown -R appuser:appuser /app

COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV HOST=0.0.0.0

COPY --chown=appuser:appuser rag_service /app/rag_service

USER appuser

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "rag_service.api.app:app", "--host", "0.0.0.0", "--port", "8001"]
