FROM python:3.12
ARG OLLAMA_MODEL=gemma:2b-q4_0

WORKDIR /app

# System dependencies - add curl here
RUN apt-get update && apt-get install -y     gcc     libgomp1     curl     && rm -rf /var/lib/apt/lists/*

# Switch to root user if necessary, though python images usually are root during build
USER root

# Install Ollama
RUN echo "Installing Ollama..." &&     curl -fsSL https://ollama.com/install.sh | sh &&     echo "Ollama installation script finished."
RUN ollama pull ${OLLAMA_MODEL}

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Switch to the non-root user
USER appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
# COPY run.sh . # Removed
# RUN chmod +x ./run.sh # Removed

RUN mkdir -p /data/{docs,database}

# Expose port for FastAPI
EXPOSE 8000
