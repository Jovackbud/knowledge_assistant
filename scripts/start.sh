#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting web server..."
# The 'exec' command is important because it replaces the shell process with the
# uvicorn process, which is what Render's process manager expects.
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}