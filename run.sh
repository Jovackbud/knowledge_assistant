#!/bin/bash

# Start Uvicorn for FastAPI in the background
echo "Starting FastAPI server with Uvicorn..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit
echo "Starting Streamlit server..."
streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
