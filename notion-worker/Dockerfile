FROM python:3.11-slim

# Installe le client Docker
RUN apt-get update && apt-get install -y docker.io && apt-get clean

WORKDIR /app

COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
