# Dockerfile

# 1. Use an official Python runtime as a parent image
# Using python:3.10-slim to match your local environment and keep the image size reasonable
FROM python:3.10-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /usr/src/app

# 4. Install dependencies
# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .
# Install the packages
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
# This includes the 'src', 'scripts', and 'prompts' directories
COPY . .

# 6. Make the startup script executable
RUN chmod +x ./render-start.sh

# 7. Define the command to run your app
# This will execute the startup script when the container launches
CMD ["bash", "./render-start.sh"]