# CapSight Backend v2 - Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash capsight
RUN chown -R capsight:capsight /app
USER capsight

# Copy application code
COPY --chown=capsight:capsight ./src /app/src
COPY --chown=capsight:capsight ./config /app/config

# Create necessary directories
RUN mkdir -p /app/logs /app/models /app/data_queue /app/mlruns /app/feature_repo

# Set Python path
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "src/main.py"]
