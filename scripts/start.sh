#!/bin/bash

# Start Ollama server in the background
echo "Starting Ollama server..."
ollama serve &

# Optional: Give Ollama a few seconds to start
sleep 5 

echo "Ollama server started. Proceeding with initialization..."

# Initialize databases and sync documents
python scripts/initialize.py

# Start Streamlit
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0