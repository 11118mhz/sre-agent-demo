FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi>=0.115.0 uvicorn>=0.32.0 httpx>=0.27.0 anthropic>=0.20.0 jinja2>=3.1.0
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
