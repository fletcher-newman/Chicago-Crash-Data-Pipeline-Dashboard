# Chicago Crash Data ETL Pipeline Dashboard

A real-time data engineering pipeline that extracts, transforms, and analyzes Chicago traffic crash data using a medallion architecture (Bronze → Silver → Gold). Features a comprehensive Streamlit dashboard for data exploration, scheduling, and reporting.

![Pipeline Architecture](https://img.shields.io/badge/Architecture-Medallion-blue)
![Language](https://img.shields.io/badge/Language-Python%20%7C%20Go-green)
![Database](https://img.shields.io/badge/Database-DuckDB-orange)

## 🎯 Project Overview

This project demonstrates end-to-end data engineering skills including:
- **Real-time ETL pipeline** processing Chicago Open Data Portal crash records
- **Medallion architecture** for data quality layers (Bronze/Raw → Silver/Transformed → Gold/Analytics)
- **Message queue orchestration** using RabbitMQ for decoupled microservices
- **Object storage** with MinIO (S3-compatible) for data lake
- **Interactive dashboard** built with Streamlit for data exploration and ML feature analysis
- **Automated scheduling** using cron jobs for periodic data ingestion
- **Containerized deployment** with Docker Compose

### Target Use Case
Predictive analytics for **hit-and-run crashes** - building features for a binary classification model to identify patterns and risk factors.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Linux/macOS (Windows with WSL2)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/fletcher-newman/Chicago-Crash-Data-Pipeline-Dashboard.git
cd Chicago-Crash-Data-Pipeline-Dashboard
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your configuration (or use defaults)
```

3. **Start the pipeline**
```bash
docker compose up -d
```

4. **Access the dashboard**
```
http://localhost:8501
```

5. **Access supporting services**
- MinIO Console: `http://localhost:9001` (admin/minioadmin)
- RabbitMQ Management: `http://localhost:15672` (guest/guest)

### Running Data Extraction

1. Navigate to the **Data Fetcher** tab in Streamlit
2. Select "Backfill" mode
3. Choose date range (e.g., last 30 days)
4. Set batch size (2000 recommended)
5. Click "Start Extraction"
6. Monitor progress in the dashboard
7. View results in the **EDA** tab once complete

## Architecture

```
┌─────────────────┐
│ Chicago Open    │
│ Data Portal     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   Extractor     │─────▶│   RabbitMQ      │
│   (Go Service)  │      │   Message Queue │
└─────────────────┘      └────────┬────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐
│  Transformer    │      │    Cleaner      │     │   Streamlit     │
│ (Enrichment)    │      │  (DuckDB Load)  │     │   Dashboard     │
└────────┬────────┘      └────────┬────────┘     └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│  MinIO Storage  │      │  DuckDB Gold    │
│  (Bronze/Silver)│      │  (Analytics DB) │
└─────────────────┘      └─────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Extraction** | Go (Golang) | High-performance API client for Chicago Data Portal |
| **Message Queue** | RabbitMQ | Decoupled microservice communication |
| **Object Storage** | MinIO | S3-compatible data lake for Bronze/Silver layers |
| **Data Transformation** | Python, Pandas | Data enrichment and cleaning |
| **Analytics Database** | DuckDB | OLAP database for Gold layer analytics |
| **Dashboard** | Streamlit | Interactive web UI for exploration and reporting |
| **Orchestration** | Docker Compose | Container management |
| **Scheduling** | Linux Cron | Automated periodic data ingestion |
| **PDF Reports** | ReportLab | Comprehensive pipeline reporting |

## Dashboard Features

### 1. **Data Fetcher Tab**
- Manual and scheduled data extraction
- Configurable date ranges and batch sizes
- Real-time extraction progress monitoring
- Integration with RabbitMQ pipeline

### 2. **Scheduler Tab**
- Cron-based job scheduling (daily, weekly, custom schedules)
- Enable/disable/delete scheduled jobs
- Job configuration management
- Next run time predictions

### 3. **EDA (Exploratory Data Analysis) Tab**
20+ interactive visualizations focused on hit-and-run analysis:
- Temporal patterns (time of day, day of week, seasonal trends)
- Geographic heatmaps of crash locations
- Weather impact analysis
- Road condition correlations
- Lighting and traffic control factor analysis
- Statistical summaries and distribution plots

### 4. **Reports Tab**
- Run history and pipeline status monitoring
- Data quality metrics
- Error tracking and debugging
- Downloadable PDF comprehensive reports

## Project Structure

```
Pipeline/
├── extractor/              # Go service for API extraction
│   ├── main.go            # HTTP client, pagination, RabbitMQ publisher
│   └── Dockerfile
├── transformer/           # Python enrichment service
│   ├── transformer.py     # Data enrichment logic
│   └── Dockerfile
├── cleaner/              # Python cleaning and DuckDB loader
│   ├── cleaner.py        # RabbitMQ consumer
│   ├── cleaning_rules.py # Data validation and cleaning
│   ├── duckdb_writer.py  # Gold table schema and insertion
│   └── Dockerfile
├── streamlit_frontend/   # Interactive dashboard
│   ├── streamlit_frontend.py  # Main dashboard app
│   ├── scheduler_tab.py       # Cron job management
│   ├── pipeline_scheduler.py  # Standalone scheduler script
│   └── Dockerfile
├── docker-compose.yaml   # Service orchestration
└── README.md            # This file
```

## Key Learning Outcomes

This project demonstrates proficiency in:

1. **Data Engineering**
   - ETL pipeline design and implementation
   - Medallion architecture (Bronze/Silver/Gold layers)
   - Data quality validation and cleaning
   - Schema design for analytics

2. **Distributed Systems**
   - Microservice architecture with message queues
   - Event-driven data processing
   - Containerization and orchestration

3. **Data Analysis & ML Preparation**
   - Feature engineering for classification models
   - Exploratory data analysis
   - Statistical analysis and visualization
   - Class imbalance handling (hit-and-run is minority class)

4. **Software Engineering**
   - Multi-language development (Python + Go)
   - Docker containerization
   - Configuration management
   - Error handling and logging

## Data Pipeline Flow

1. **Bronze Layer (Raw)**
   - Extractor fetches raw JSON from Chicago Data Portal
   - Stores in MinIO with correlation IDs for tracking
   - Publishes transform job to RabbitMQ

2. **Silver Layer (Transformed)**
   - Transformer enriches data with additional datasets
   - Normalizes and validates data structure
   - Stores enriched JSON in MinIO
   - Publishes clean job to RabbitMQ

3. **Gold Layer (Analytics)**
   - Cleaner applies business rules and validation
   - Loads cleaned data into DuckDB (OLAP database)
   - Optimized schema for analytical queries
   - Accessible via Streamlit dashboard

## Future Enhancements

- [ ] Machine learning model for hit-and-run prediction
- [ ] Real-time streaming with Apache Kafka
- [ ] dbt for transformation logic
- [ ] Airflow for workflow orchestration
- [ ] AWS/GCP deployment
- [ ] API endpoint for model serving

## Author

**Fletcher Newman**
- GitHub: [@fletcher-newman](https://github.com/fletcher-newman)
- Email: fletcht13@gmail.com
