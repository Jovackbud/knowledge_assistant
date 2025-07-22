# Dockerfile

# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /usr/src/app

# 4. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Make the startup script executable (as root)
RUN chmod +x ./render-start.sh

# Create the directory where databases and caches will be stored.
# This directory will also be the mount point for Render's persistent disk.
RUN mkdir -p /usr/src/app/database /usr/src/app/cache

# 7. Create the non-root user
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# --- NEW: Assign ownership of the data directories to the new user ---
RUN chown -R appuser:appgroup /usr/src/app/database /usr/src/app/cache

# 8. Switch to the non-root user for security
USER appuser

# 9. Switch BACK to the root user before the CMD instruction.
# This ensures the render-start.sh script itself runs as root,
# giving it the necessary permissions to chown the mounted disk.
USER root

# 10. Define the command to run your app
CMD ["bash", "./render-start.sh"]