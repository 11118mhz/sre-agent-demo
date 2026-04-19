FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir anthropic>=0.20.0 httpx>=0.27.0

COPY app.py .

CMD ["python", "app.py"]
