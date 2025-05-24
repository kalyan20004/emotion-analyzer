# Use a specific and stable Python base image
FROM python:3.10.12-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies in a single layer and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    libffi-dev \
    ca-certificates \
    curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Update CA certificates for SSL connections
RUN update-ca-certificates

# Copy requirements file separately to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Don't include credentials here - they should come from environment variables
    # at runtime or through render.yaml
    DB_NAME="emotion_analyzer"

# Copy the application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI app using Uvicorn with a single worker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]