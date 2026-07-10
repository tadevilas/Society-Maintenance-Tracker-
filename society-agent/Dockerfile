# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps only in this layer
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Metadata
LABEL org.opencontainers.image.title="Society Maintenance Agent"
LABEL org.opencontainers.image.description="LangGraph + FastAPI + Streamlit society maintenance agent"
LABEL org.opencontainers.image.source="https://github.com/$GITHUB_REPOSITORY"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (excludes anything in .dockerignore)
COPY . .

# Create a non-root user WITH a real home directory.
# --system users get home=/nonexistent by default which breaks Streamlit's
# machine-ID file write. --home /home/appuser gives it a writable location.
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /home/appuser appuser \
    && mkdir -p /home/appuser /app/agent /app/data /app/reports \
    && chown -R appuser:appgroup /app /home/appuser

USER appuser

# Both services expose their ports – only the relevant one is used per container
EXPOSE 8000 8501

# Default command: override in docker-compose or at runtime
# e.g. --service api  → FastAPI  (port 8000)
#      --service ui   → Streamlit (port 8501)
CMD ["streamlit", "run", "ui/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
