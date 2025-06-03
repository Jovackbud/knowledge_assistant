FROM python:3.12

WORKDIR /app

# System dependencies - add curl here
RUN apt-get update && apt-get install -y     gcc     libgomp1     curl     && rm -rf /var/lib/apt/lists/*

# Switch to root user if necessary, though python images usually are root during build
USER root

# Install Ollama
RUN echo "Installing Ollama..." &&     curl -fsSL https://ollama.com/install.sh | sh &&     echo "Ollama installation script finished."

# Ensure Ollama is in PATH - the install script should handle this.
# If not, common locations are /usr/local/bin/ollama or /opt/ollama/ollama
ENV OLLAMA_MODELS=/root/.ollama/models

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN mkdir -p /data/{docs,database}
RUN mkdir -p ${OLLAMA_MODELS} # Ensure the models directory exists

# Expose port for FastAPI
EXPOSE 8000
# EXPOSE 8501 # Removed, as this image is now FastAPI-only

# Pull the LLM model - This is now handled by entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
