#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Application Deployment ---"

# Define paths for persistent data.
DATA_DIR="database"
CACHE_DIR="cache"

echo "Step 1: Setting runtime permissions on persistent disk mounts..."
# This part runs as root, as confirmed by the logs.
echo "Current user: $(whoami)"
# This command correctly fixes permissions on the mounted volumes.
chown -R appuser:appgroup "$DATA_DIR" "$CACHE_DIR"
echo "Permissions set successfully."

# Now, run the initialization script as the 'appuser'.
# The syntax `su -c "command" <user>` is the most portable.
echo "Step 2: Running initialization script as 'appuser'..."
su -c "python -m scripts.initialize" appuser

# Verification Step.
echo "Step 3: Verifying initialization results..."
if [ ! -f "$DATA_DIR/auth_profiles.db" ]; then
    echo "CRITICAL FAILURE: Initialization did not create the auth database."
    exit 1
else
    echo "Verification successful: Auth database found."
fi

# Finally, start the web server as the 'appuser'.
# The `exec` ensures Uvicorn replaces this script's process and receives signals correctly.
echo "Step 4: Starting the Uvicorn web server as 'appuser'..."
exec su -c "uvicorn src.main:app --host 0.0.0.0 --port \${PORT:-8000}" appuser