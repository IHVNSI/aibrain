FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend . 

# Copy docs folder from project root
COPY docs /docs

# Ensure static directory exists for Swagger UI assets
RUN mkdir -p /app/app/static /app/data/vanna_chroma /app/data/vanna_faiss \
  && useradd --system --no-create-home --shell /bin/false appuser \
  && chown -R appuser:appuser /app /docs
ENV HOME=/app/data \
    HF_HOME=/app/data/huggingface \
    TRANSFORMERS_CACHE=/app/data/huggingface \
    XDG_CACHE_HOME=/app/data/.cache \
    DOCS_FOLDER=/docs
USER appuser

EXPOSE 5001
CMD ["python", "run.py"]
