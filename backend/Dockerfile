
# Multi-stage Production Dockerfile for AI Customer Support Backend

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend_requirements.txt
COPY rag_service/requirements.txt ./rag_requirements.txt

RUN pip install --no-cache-dir --user -r backend_requirements.txt -r rag_requirements.txt


# Stage 2: Production runtime
FROM python:3.12-slim AS runner

WORKDIR /app

# Install curl for Docker health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Copy installed Python packages
COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/home/appuser/.local/lib/python3.12/site-packages:/app:/app/backend:/app/rag_service

# Copy backend and RAG application
COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup rag_service /app/rag_service
COPY --chown=appuser:appgroup frontend /app/frontend

# Copy SQLite source files (not the local database binary)
COPY --chown=appuser:appgroup database/*.py /app/database/
COPY --chown=appuser:appgroup database/*.sql /app/database/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
