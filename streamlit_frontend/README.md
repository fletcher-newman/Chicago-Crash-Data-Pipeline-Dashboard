# Chicago Crash ETL Dashboard

A Streamlit-based web dashboard for managing and monitoring the Chicago Crash ETL pipeline.

## Features

### ✅ Implemented:
- **🏠 Home Tab**:
  - ML Pipeline overview with label descriptions
  - Container health status for all services (MinIO, RabbitMQ, Extractor, Transformer, Cleaner)
  - Quick access links

### 🚧 Coming Soon:
- **🧰 Data Management Tab**: Manage MinIO storage and Gold database
- **🔍 Data Fetcher Tab**: Trigger streaming and backfill data fetches
- **⏰ Scheduler Tab**: Schedule automated pipeline runs
- **📊 EDA Tab**: Exploratory data analysis with visualizations
- **📑 Reports Tab**: Pipeline metrics and downloadable reports

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

1. Make sure your Docker containers are running:
```bash
docker compose up -d
```

2. Start the Streamlit app:
```bash
streamlit run streamlit_frontend.py
```

3. Open your browser to the URL shown (typically http://localhost:8501)

## Configuration

The dashboard connects to your backend API at `http://localhost:8000/api` by default.

To change this, edit the `API_BASE_URL` variable at the top of `streamlit_frontend.py`:

```python
API_BASE_URL = "http://your-backend-host:port/api"
```

## Project Structure

```
streamlit_frontend/
├── streamlit_frontend.py    # Main dashboard application
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── streamlit_instructions.md # Full project requirements
```

## Notes

- The health check functionality requires a backend API with `/api/health/{service}` endpoints
- You may need to implement these endpoints in your backend if they don't exist yet
- The dashboard uses Streamlit's caching to improve performance
