FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 🔧 Autorise le passage d'arguments à sync_and_embed.py
ENTRYPOINT ["python", "sync_and_embed.py"]
