FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn>=0.32.0 \
    chromadb>=0.4.0 \
    sentence-transformers>=2.2.0
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8005"]
