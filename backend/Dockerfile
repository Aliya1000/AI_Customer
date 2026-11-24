# Multi-stage Production Dockerfile for AI Customer Support Backend
# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend_requirements.txt
COPY rag_service/requirements.txt ./rag_requirements.txt

RUN pip install --no-cache-dir --user -r backend_requirements.txt -r rag_requirements.txt

# Stage 2: Final Production Runtime
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root app user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/backend:/app/rag_service

# Copy application source code
COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup rag_service /app/rag_service

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
