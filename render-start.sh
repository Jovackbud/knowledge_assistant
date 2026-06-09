#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Step 1/3: Checking Pinecone index dimensions and migrating if needed..."
# Idempotent: if dimensions already match, this exits in seconds with no changes.
python -m scripts.migrate_pinecone_index

echo "Step 2/3: Running DB schema check and sample user initialization..."
python -m scripts.initialize

echo "Step 3/3: Initialization complete. Starting web server..."
# The 'exec' command replaces the shell process so uvicorn receives signals directly.
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}