# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables to avoid OpenMP affinity errors
ENV KMP_AFFINITY=disabled
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV KMP_BLOCKTIME=0

# Install system dependencies
RUN apt-get update && \
    apt-get install -y git gcc wget unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY gen_embeddings.py /app/gen_embeddings.py
WORKDIR /app

COPY ./cache /app/cache
ENV TRANSFORMERS_CACHE=/app/cache

# Command to run your script by default
CMD ["python", "gen_embeddings.py"]

