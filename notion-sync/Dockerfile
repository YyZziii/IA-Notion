FROM python:3.11-slim

WORKDIR /app

COPY notion-sync/ ./
COPY shared/ ./shared

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/app"

ENTRYPOINT ["python", "main.py"]
