# cleaner/Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for Gold database (will be mounted as volume)
RUN mkdir -p /data/gold

# Expose metrics port
EXPOSE 8000

# Run the cleaner
CMD ["python", "-u", "cleaner.py"]
