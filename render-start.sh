#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running initialization script..."
# Run the database and document initialization.
# This will create users and sync documents on the very first boot.
# On subsequent boots, it will run quickly as everything already exists.
# python scripts/initialize.py

echo "Initialization complete. Starting web server..."
# Start the Uvicorn server.
# The 'exec' command is important because it replaces the shell process with the
# uvicorn process, which is what Render's process manager expects.
exec uvicorn src.main:app --host 0.0.0.0 --port 8000