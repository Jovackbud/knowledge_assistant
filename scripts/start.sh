#!/bin/bash
# Start FastAPI backend
echo "Starting FastAPI backend..."
uvicorn src.main:app --host 0.0.0.0 --port 8000