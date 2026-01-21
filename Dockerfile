# JobForge FastAPI Application Container
# Multi-platform support: AMD64 and ARM64

FROM python:3.11-slim

# Install curl for healthchecks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency metadata first for Docker layer caching
COPY pyproject.toml .

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Copy application code and catalog metadata
COPY src/ ./src/
COPY data/catalog/ ./data/catalog/
COPY orbit/ ./orbit/

# Expose FastAPI port
EXPOSE 8000

# Use exec form for proper signal handling
CMD ["uvicorn", "jobforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
