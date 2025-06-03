#!/bin/bash
set -e

# Start Ollama server in the background
echo "Starting Ollama server..."
/usr/local/bin/ollama serve &
OLLAMA_PID=$!
echo "Ollama server started with PID $OLLAMA_PID."

# Wait a few seconds for Ollama to be ready
# A more robust check would be to poll its health endpoint, but sleep is simpler for now.
sleep 5

# Pull the LLM model if LLM_MODEL is set
if [ -n "$LLM_MODEL" ]; then
  echo "Pulling LLM model: $LLM_MODEL..."
  ollama pull "$LLM_MODEL"
  echo "LLM model pull initiated (or model already exists)."
else
  echo "LLM_MODEL environment variable not set. Skipping model pull."
  echo "Ensure a model is available in the Ollama models directory if you intend to use one."
fi

# Execute the CMD from the Dockerfile (e.g., uvicorn)
echo "Executing command: $@"
exec "$@"
