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

# Create startup script that runs both cron and Streamlit
RUN echo '#!/bin/bash\n\
# Start cron daemon\n\
cron\n\
# Start Streamlit in foreground\n\
streamlit run streamlit_frontend.py --server.address=0.0.0.0 --server.port=8501\n\
' > /start.sh && chmod +x /start.sh

# Run startup script
CMD ["/start.sh"]
