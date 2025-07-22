#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Application Deployment ---"

# Define the paths for our persistent data directories.
DATA_DIR="database"
CACHE_DIR="cache"

# --- THE CRITICAL FIX ---
# At runtime, Render mounts a persistent disk at the location specified in
# render.yaml (e.g., /usr/src/app/database). This new mount point is owned by root.
# We must change the ownership of this mounted directory to our application user
# *before* the application tries to write to it.
echo "Step 1: Setting runtime permissions on persistent disk mounts..."
# The 'whoami' command will show that this part of the script runs as root.
echo "Current user: $(whoami)"
chown -R appuser:appgroup "$DATA_DIR" "$CACHE_DIR"
echo "Permissions set successfully."

# Now that permissions are correct, run the initialization script as the app user.
# We use 'su-exec' to drop from root to our specific appuser for this command.
echo "Step 2: Running initialization script as 'appuser'..."
su-exec appuser python -m scripts.initialize

# Verification Step: Check if initialization worked.
echo "Step 3: Verifying initialization results..."
if [ ! -f "$DATA_DIR/auth_profiles.db" ]; then
    echo "CRITICAL FAILURE: Initialization did not create the auth database."
    exit 1
else
    echo "Verification successful: Auth database found."
fi

# Finally, drop privileges permanently and start the web server as the app user.
echo "Step 4: Starting the Uvicorn web server as 'appuser'..."
exec su-exec appuser uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}