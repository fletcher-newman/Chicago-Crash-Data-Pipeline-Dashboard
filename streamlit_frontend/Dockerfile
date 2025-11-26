# streamlit_frontend/Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (cron for scheduler)
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Expose Prometheus metrics port
EXPOSE 8000

# Create prometheus multiprocess directory
RUN mkdir -p /tmp/prometheus_multiproc

# Create metrics server script that uses multiprocess mode
RUN echo 'from prometheus_client import start_http_server, CollectorRegistry, REGISTRY\n\
from prometheus_client.multiprocess import MultiProcessCollector\n\
import time\n\
import os\n\
\n\
# Set up multiprocess mode\n\
registry = CollectorRegistry()\n\
MultiProcessCollector(registry)\n\
\n\
print("Starting metrics server on port 8000 with multiprocess support...")\n\
start_http_server(8000, registry=registry)\n\
print("Metrics server started successfully")\n\
print("Using multiprocess directory: /tmp/prometheus_multiproc")\n\
# Keep running\n\
while True:\n\
    time.sleep(60)\n\
' > /app/metrics_server.py

# Create startup script that runs metrics server, cron, and Streamlit
RUN echo '#!/bin/bash\n\
# Set prometheus multiprocess directory\n\
export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc\n\
# Clean any old metrics\n\
rm -rf /tmp/prometheus_multiproc/*\n\
# Start metrics server in background\n\
python3 /app/metrics_server.py &\n\
sleep 2\n\
# Start cron daemon\n\
cron\n\
# Start Streamlit in foreground\n\
streamlit run streamlit_frontend.py --server.address=0.0.0.0 --server.port=8501\n\
' > /start.sh && chmod +x /start.sh

# Run startup script
CMD ["/start.sh"]
