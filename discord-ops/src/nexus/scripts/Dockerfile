# CHRONOS-FORGE DEDI-AGENT DOCKERFILE
# Stage 1: Build stage with all dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    psmisc \
    fuser \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    fastapi \
    uvicorn[standard] \
    orjson \
    uvloop \
    pydantic \
    gitpython \
    aiofiles \
    websockets \
    httpx

# Stage 2: Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /usr/bin/fuser /usr/bin/fuser
COPY --from=builder /usr/bin/ps /usr/bin/ps

# Update PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY main.py dedi_agent.py /app/

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:35100/health || exit 1

# Expose port
EXPOSE 35100

# Run via main.py (safeguard entrypoint)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "35100", "--loop", "uvloop", "--log-level", "info"]
