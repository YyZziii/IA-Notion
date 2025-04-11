FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de notion-sync
COPY notion-sync/ ./

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/app"

ENTRYPOINT ["python", "main.py"]
