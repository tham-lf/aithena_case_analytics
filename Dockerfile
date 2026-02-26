# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Playwright and subprocesses
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browser dependencies (Chromium)
RUN playwright install --with-deps chromium

# Copy the current directory contents into the container at /app
COPY . .

# Ensure data directory exists (this will be the mount point for persistent volume)
RUN mkdir -p data

# Make the start script executable
RUN chmod +x start.sh

# Expose ports (FastAPI: 8000, Streamlit: Default $PORT)
EXPOSE 8000

# Run the startup script
CMD ["./start.sh"]
