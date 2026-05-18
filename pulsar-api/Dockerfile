FROM python:3.11-slim

# Correction de la casse pour les standards Docker (FROM / AS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .
COPY server.py .

# Exposition du port requis par la Gateway OpenFaaS
EXPOSE 8080

CMD ["python", "server.py"]