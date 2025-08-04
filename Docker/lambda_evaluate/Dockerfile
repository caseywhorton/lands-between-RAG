FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install numpy first to avoid compatibility issues
RUN pip install --upgrade pip
RUN pip install --no-cache-dir numpy==1.24.4

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy test queries and source files
COPY test_queries.json .
COPY app/ .

# Download nltk data
RUN python3 -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Set environment variables (these should be passed at runtime)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the evaluate script
CMD ["python", "evaluate.py"]