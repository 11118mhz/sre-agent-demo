FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn>=0.32.0 \
    chromadb>=0.4.0 \
    sentence-transformers>=2.2.0

# Pre-download the embedding model at build time
# so cold starts don't need to fetch it from HuggingFace
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"]
