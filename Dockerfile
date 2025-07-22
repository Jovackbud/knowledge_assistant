# Dockerfile

# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /usr/src/app

# 4. Install dependencies
# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
# This is done as the ROOT user.
COPY . .

# 6. Make the web server startup script executable
# This MUST be done as the ROOT user, BEFORE switching to the appuser.
# We are now using the correct script: render-start.sh
RUN chmod +x ./render-start.sh

# 7. Create a non-root user and group
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# 8. Switch to the non-root user for security
USER appuser

# 9. Define the command to run your app
# This executes the web server startup script as the 'appuser'
CMD ["bash", "./render-start.sh"]