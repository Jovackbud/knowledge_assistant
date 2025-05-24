FROM python:3.12

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/

RUN mkdir -p /data/{docs,database}

CMD ["bash", "scripts/start.sh"]