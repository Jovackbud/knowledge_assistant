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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/

RUN mkdir -p /data/{docs,database}

# Pull the LLM model
# This command is executed by the ollama CLI after its installation.

CMD ["bash", "scripts/start.sh"]
