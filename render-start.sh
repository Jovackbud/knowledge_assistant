#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running initialization script (for DB schema check and sample users)..."
# This now just checks the schema and adds users if needed. It's fast.
python -m scripts.initialize

echo "Initialization complete. Starting web server..."
# The 'exec' command is important because it replaces the shell process.
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}