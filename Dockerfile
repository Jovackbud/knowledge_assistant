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

# 6. Make the startup script executable
RUN chmod +x ./render-start.sh

# 7. Create and switch to a non-root user for security
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser
USER appuser

# 8. Define the command to run your app
CMD ["bash", "./render-start.sh"]