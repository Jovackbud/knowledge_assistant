#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Application Deployment ---"

# Define the path to a critical database file that MUST exist after initialization.
AUTH_DB="database/auth_profiles.db"

# Run the initialization script.
# We explicitly pipe output to ensure it's captured in logs.
echo "Step 1: Running initialization script..."
python -m scripts.initialize

# Verification Step: Check if the initialization actually created the database.
echo "Step 2: Verifying initialization results..."
if [ ! -f "$AUTH_DB" ]; then
    echo "CRITICAL FAILURE: Initialization script completed but the auth database ('$AUTH_DB') was not found."
    echo "This indicates a silent failure during initialization. Aborting startup."
    exit 1
else
    echo "Verification successful: Auth database found at '$AUTH_DB'."
fi

# If verification passes, start the web server.
echo "Step 3: Starting the Uvicorn web server..."
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}