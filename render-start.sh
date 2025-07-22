#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- FREE-TIER WORKAROUND ---
# On the free tier, we cannot use a separate initialization job.
# Therefore, we run the initialization script here, as part of the
# web server's startup command. This will run ONCE every time the
# server starts or restarts.

echo "Running initialization script..."
python -m scripts.initialize

# After the initialization is complete, start the web server.
# The 'exec' command replaces the shell process with the uvicorn process,
# which is what Render's process manager expects.
echo "Initialization complete. Starting web server..."
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
