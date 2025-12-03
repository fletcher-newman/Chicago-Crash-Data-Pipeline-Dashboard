# Chicago Crash Data Pipeline & ML Dashboard

A production-ready data engineering and machine learning pipeline that processes Chicago traffic crash data through a multi-stage ETL workflow, trains a hit-and-run prediction model, and provides real-time visualization and monitoring capabilities.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Pipeline Components](#pipeline-components)
- [Technology Stack](#technology-stack)
- [Setup Instructions](#setup-instructions)
- [Running the Pipeline](#running-the-pipeline)
- [Accessing Services](#accessing-services)
- [Screenshots](#screenshots)
- [Improvements & Extensions](#improvements--extensions)
- [Challenges & Lessons Learned](#challenges--lessons-learned)

---

## 🎯 Overview

### Problem Statement

Chicago experiences thousands of traffic crashes annually, with hit-and-run incidents posing significant challenges for law enforcement and public safety. This pipeline addresses the need to:

- **Automate data collection** from the Chicago Data Portal's Crash API
- **Process and clean** large-scale crash, vehicle, and people datasets
- **Predict hit-and-run incidents** using machine learning
- **Monitor pipeline health** in real-time with production-grade observability tools

### Solution

This end-to-end data pipeline implements a **medallion architecture** (Bronze → Silver → Gold) to progressively refine raw crash data into analysis-ready datasets. The system:

1. **Extracts** raw crash, vehicle, and people data from the Chicago Data Portal API
2. **Transforms** and merges the data into unified Silver-layer CSVs
3. **Cleans** and validates data before loading into a DuckDB Gold database
4. **Trains** an XGBoost classifier to predict hit-and-run crashes
5. **Visualizes** insights and predictions through an interactive Streamlit dashboard
6. **Monitors** all components using Prometheus metrics and Grafana dashboards

### Data Sources

- **Chicago Traffic Crashes API**: Crash-level details including date, time, location, conditions
- **Chicago Vehicles API**: Vehicle information involved in each crash
- **Chicago People API**: People involved (injuries, demographics, fault)

All data flows through MinIO (S3-compatible storage) and RabbitMQ (message queue) to ensure reliability and scalability.

---

## 🏗️ Pipeline Architecture

### Data Flow Diagram

*[You can add your custom architecture diagram here using tools like Excalidraw, Draw.io, or Mermaid]*

### Simplified Data Flow

```
Chicago APIs → Extractor (Go) → MinIO (Bronze) → RabbitMQ
                                      ↓
                              Transformer (Python) → MinIO (Silver) → RabbitMQ
                                      ↓
                              Cleaner (Python) → DuckDB (Gold)
                                      ↓
                              Streamlit Dashboard ← ML Model (XGBoost)
                                      ↓
                              Prometheus ← Metrics → Grafana Dashboards
```

### Architecture Layers

- **Bronze Layer**: Raw API responses stored as-is in MinIO
- **Silver Layer**: Merged and validated data, ready for analysis
- **Gold Layer**: Cleaned, feature-engineered data in DuckDB for ML and dashboards

---

## 🔧 Pipeline Components

### 1. Extractor (Go)

**Purpose**: High-performance data extraction from Chicago Data Portal APIs

The extractor service, written in Go for speed and concurrency, pulls raw crash, vehicle, and people records from the Chicago Data Portal's Socrata API. It supports both backfill mode (historical data) and streaming mode (incremental updates). Raw data is stored in MinIO's Bronze layer and a message is published to RabbitMQ to trigger downstream processing.

**Key Features**:
- Concurrent API requests for faster extraction
- Automatic pagination handling
- Retry logic for failed API calls
- Prometheus metrics for monitoring extraction performance

![Extractor Running](README-assets/extractor_running.png)

---

### 2. Transformer (Python)

**Purpose**: Data merging and initial cleaning

The transformer consumes messages from RabbitMQ, retrieves raw Bronze CSVs from MinIO, and performs data merging, schema validation, type conversion, and deduplication. The merged data is written to MinIO's Silver layer as cleaned CSVs, and a new message is published to trigger the cleaner stage.

**Key Features**:
- Joins crash, vehicle, and people datasets on record IDs
- Standardizes data types and handles missing values
- Removes duplicate records
- Validates schema before publishing to Silver layer

![Transformer Running](README-assets/transformer_running.png)

---

### 3. Cleaner (Python)

**Purpose**: Advanced data cleaning and loading into the Gold database

The cleaner applies business logic and data quality rules including null handling, feature engineering, outlier removal, and validation. Cleaned data is loaded into DuckDB (embedded analytical database) in the Gold layer, making it ready for ML model training and dashboard queries.

**Key Features**:
- Fills missing coordinates with median values
- Creates binned features (lat_bin, lng_bin, hour_bin)
- Filters invalid or suspicious records
- Ensures data integrity before database insertion

![Cleaner Running](README-assets/cleaner_running.png)

---

### 4. Streamlit Dashboard

**Purpose**: Interactive web interface for data exploration, ML training, and predictions

The Streamlit application provides a comprehensive UI with multiple tabs for managing the entire pipeline, training machine learning models, and generating insights.

**Dashboard Tabs**:

- **Home**: Pipeline overview, service health checks, and quick access links
- **Data Management**: Browse MinIO buckets and Gold database tables
- **Data Fetcher**: Trigger backfill or streaming data extractions
- **Scheduler**: Schedule automated pipeline runs using cron expressions
- **EDA (Exploratory Data Analysis)**: Interactive visualizations of crash patterns
- **Reports**: Generate and download PDF reports of pipeline metrics
- **Model**: Train XGBoost models and make hit-and-run predictions

The ML model uses features like crash time, location, lighting conditions, road conditions, and injury counts to predict whether a crash will result in a hit-and-run incident with approximately 55% F1 score.

![Streamlit Home Page](README-assets/streamlit_home_page.png)

![Streamlit Model Training](README-assets/streamlit_model_train.png)

![Streamlit Model Predictions](README-assets/streamlit_model_predict.png)

---

### 5. Monitoring Stack (Prometheus & Grafana)

**Purpose**: Real-time observability and performance monitoring

Every pipeline component exposes Prometheus metrics on port 8000, providing comprehensive visibility into pipeline performance and health.

**Monitored Metrics**:

- **Extractor**: Records fetched, API response times, error rates
- **Transformer**: Merge operations, processing duration, message queue lag
- **Cleaner**: Rows cleaned, database write performance, data quality scores
- **Streamlit**: Page loads, model predictions, user interactions
- **RabbitMQ**: Queue depth, message rates, consumer lag
- **MinIO**: Storage usage, object counts, request latencies

Prometheus scrapes these metrics every 5 seconds, and Grafana provides customizable dashboards for visualization and alerting.

![Prometheus Target Health](README-assets/prometheus_target_health.png)

![Grafana Dashboard 1](README-assets/grafana_dashboard_1.png)

![Grafana Dashboard 2](README-assets/grafana_dashboard_2.png)

---

### 6. Docker Compose Orchestration

**Purpose**: Simplified deployment and service coordination

All services run as Docker containers orchestrated by Docker Compose:

- **MinIO**: S3-compatible object storage for Bronze and Silver data
- **RabbitMQ**: Message queue for pipeline stage coordination
- **Extractor, Transformer, Cleaner**: Core ETL components
- **Streamlit**: Web dashboard and ML interface
- **Prometheus**: Metrics collection and time-series database
- **Grafana**: Metrics visualization and alerting
- **RabbitMQ Exporter**: Additional monitoring for message queues

This architecture ensures isolation, scalability, portability, and reproducibility across development and production environments.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Extraction** | Go, Socrata API Client | Fast, concurrent API calls |
| **Storage** | MinIO (S3), DuckDB | Object storage + analytical database |
| **Processing** | Python, Pandas, NumPy | Data transformation and cleaning |
| **Messaging** | RabbitMQ | Reliable pipeline coordination |
| **ML** | XGBoost, scikit-learn | Classification model |
| **Frontend** | Streamlit, Plotly | Interactive dashboards |
| **Monitoring** | Prometheus, Grafana | Metrics and visualization |
| **Orchestration** | Docker, Docker Compose | Containerization and deployment |

---

## 🚀 Setup Instructions

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** for version control
- Minimum **4GB RAM** and **10GB disk space**

### 1. Clone the Repository

```bash
git clone https://github.com/fletcher-newman/Chicago-Crash-Data-Pipeline-Dashboard.git
cd Chicago-Crash-Data-Pipeline-Dashboard
```

### 2. Create Environment File

Copy the sample environment file and configure your credentials:

```bash
cp .env.sample .env
nano .env
```

Required environment variables:

```env
# MinIO Configuration
MINIO_USER=admin
MINIO_PASS=your_secure_password
MINIO_ENDPOINT=minio:9000
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

# RabbitMQ Configuration
RABBIT_USER=guest
RABBIT_PASS=guest
RABBIT_URL=amqp://guest:guest@rabbitmq:5672/
RABBIT_PORT=5672
RABBIT_UI=15672

# Data Paths
GOLD_DB_PATH=/data/gold/gold.duckdb

# Prometheus/Grafana (for Azure deployment)
UID=1000
GID=1000
```

### 3. Create Required Directories

```bash
mkdir -p data/gold
mkdir -p minio-data
mkdir -p prometheus_data
mkdir -p grafana_data
```

### 4. Set Proper Permissions

```bash
# General permissions
sudo chown -R $USER:$USER data minio-data prometheus_data grafana_data
chmod -R 755 data minio-data prometheus_data grafana_data

# Grafana requires specific UID (472)
sudo chown -R 472:472 grafana_data
```

---

## 🏃 Running the Pipeline

### Start All Services

```bash
docker compose up -d
```

This command starts all containers in detached mode. Initial startup takes 1-2 minutes.

### Verify Services are Running

```bash
docker ps
```

You should see 9 containers running:
- `rabbitmq`, `minio`, `extractor`, `transformer`, `cleaner`, `streamlit`, `prometheus`, `grafana`, `rabbitmq-exporter`

### Check Container Logs

```bash
# View all logs
docker compose logs

# Follow specific service logs
docker logs -f extractor
docker logs -f transformer
docker logs -f cleaner
docker logs -f streamlit
```

### Run a Backfill (Extract Historical Data)

1. Open the Streamlit dashboard: `http://localhost:8501`
2. Navigate to the **Data Fetcher** tab
3. Upload your `backfill.json` configuration file or configure manually
4. Click "Trigger Backfill"
5. Monitor logs to watch data flow through the pipeline
6. View results in the **EDA** or **Model** tabs

### Stop the Pipeline

```bash
docker compose down
```

To also remove volumes (delete all data):

```bash
docker compose down -v
```

---

## 🌐 Accessing Services

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Streamlit Dashboard** | http://localhost:8501 | None |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | None |
| **MinIO Console** | http://localhost:9001 | (set in .env) |
| **RabbitMQ Management** | http://localhost:15672 | guest / guest |

### Viewing Data

**Query DuckDB Gold Database:**

```bash
docker exec cleaner python3 << 'EOF'
import duckdb
conn = duckdb.connect('/data/gold/gold.duckdb', read_only=True)
result = conn.execute("SELECT COUNT(*) as total_crashes FROM crashes").fetchone()
print(f"Total crashes in Gold database: {result[0]:,}")
conn.close()
EOF
```

**Browse MinIO Buckets:**

Access the MinIO console at `http://localhost:9001` to view:
- `bronze-layer/crash/`, `bronze-layer/vehicle/`, `bronze-layer/people/`
- `silver-layer/crash/`
- `transform-data/crash/`

---

## 📸 Screenshots

### Pipeline Execution

All three ETL stages running successfully and processing crash data:

**Extractor Service** - Fetching data from Chicago Data Portal APIs:

![Extractor Running](README-assets/extractor_running.png)

**Transformer Service** - Merging crash, vehicle, and people datasets:

![Transformer Running](README-assets/transformer_running.png)

**Cleaner Service** - Loading cleaned data into DuckDB Gold database:

![Cleaner Running](README-assets/cleaner_running.png)

---

### Streamlit Dashboard

Interactive web interface for pipeline management and machine learning:

**Home Page** - Pipeline overview and service health monitoring:

![Streamlit Home](README-assets/streamlit_home_page.png)

**Model Training** - Train XGBoost classifier to predict hit-and-run crashes:

![Model Training](README-assets/streamlit_model_train.png)

**Model Predictions** - Make predictions on new crash data:

![Model Predictions](README-assets/streamlit_model_predict.png)

---

### Monitoring & Observability

Real-time metrics and health monitoring with Prometheus and Grafana:

**Prometheus Targets** - All services reporting metrics successfully:

![Prometheus Targets](README-assets/prometheus_target_health.png)

**Grafana Dashboard 1** - Pipeline performance metrics:

![Grafana Dashboard 1](README-assets/grafana_dashboard_1.png)

**Grafana Dashboard 2** - System resource monitoring:

![Grafana Dashboard 2](README-assets/grafana_dashboard_2.png)

---

## ✨ Improvements & Extensions

### Implemented Enhancements

1. **Prometheus Multiprocess Mode**
   - Fixed metric sharing across Streamlit's multiple worker processes
   - Implemented shared multiprocess directory for accurate metric collection
   - Ensures all user interactions and predictions are properly tracked

2. **Comprehensive Data Quality Checks**
   - Null value imputation using median coordinates for missing location data
   - Outlier detection and removal for invalid crash records
   - Schema validation at each pipeline stage to ensure data integrity

3. **Production-Ready Error Handling**
   - RabbitMQ message acknowledgment with retry logic for failed processing
   - Graceful degradation when upstream services are temporarily unavailable
   - Structured error logging for debugging and monitoring

4. **Interactive Scheduling System**
   - Cron-based scheduler for automated pipeline runs (daily, weekly, custom)
   - User-friendly UI for configuring and managing scheduled jobs
   - Next run time predictions and job execution history

5. **ML Model Metadata Tracking**
   - Model version, training timestamp, and performance metrics automatically saved
   - Streamlit displays model lineage and historical metrics
   - Reproducible model artifacts for deployment and comparison

### Future Improvements

- **Workflow Orchestration**: Migrate to Airflow or Prefect for complex DAG management
- **Data Versioning**: Implement DVC or lakeFS for reproducible datasets and experiments
- **Model Registry**: Add MLflow for model versioning, A/B testing, and deployment tracking
- **Real-time Streaming**: Replace batch processing with Kafka for true real-time ingestion
- **Advanced ML**: Experiment with deep learning, ensemble methods, and hyperparameter tuning
- **REST API**: Build FastAPI backend for programmatic access to predictions
- **Alerting**: Integrate PagerDuty or Slack notifications for pipeline failures
- **Data Catalog**: Add Apache Atlas or DataHub for data discovery and lineage

---

## 🎓 Challenges & Lessons Learned

### Technical Challenges

#### 1. DuckDB Version Compatibility
- **Problem**: Database files created with one DuckDB version couldn't be read by another, causing serialization errors
- **Solution**: Pinned DuckDB to version 0.10.0 across all containers and deleted incompatible database files
- **Lesson**: Version pinning is critical for reproducibility, especially for databases with binary file formats

#### 2. Pandas Segmentation Faults on Azure VM
- **Problem**: Pandas 2.0.3 crashed with exit code 139 (SIGSEGV) on Python 3.12 when reading CSV files
- **Solution**: Upgraded to Pandas 2.2.0 and NumPy 1.26.4 which have pre-built wheels for Python 3.12
- **Lesson**: Newer package versions often have better compatibility; avoid building from source when wheels are available

#### 3. Prometheus Metrics Not Updating
- **Problem**: Streamlit runs multiple worker processes, each with its own metric registry, so metrics weren't aggregated
- **Solution**: Implemented Prometheus multiprocess mode with a shared `/tmp/prometheus_multiproc` directory
- **Lesson**: Multiprocess applications require special metric handling; the default Prometheus client doesn't support multiprocessing

#### 4. Volume Mount Permissions on Azure
- **Problem**: Grafana container couldn't write to mounted volumes due to permission mismatches
- **Solution**: Set directory ownership to UID 472 (Grafana's internal user) before starting containers
- **Lesson**: Container user permissions must match host directory permissions, especially on cloud VMs

#### 5. Python 3.12 Build Dependencies
- **Problem**: Docker build failed because Python 3.12 doesn't include `setuptools` by default
- **Solution**: Used newer package versions with pre-built wheels instead of building from source
- **Lesson**: Understand build-time vs runtime dependencies; minimize compilation during builds

### Key Learnings

- **Testing on Target Platform**: Code that works locally may fail in cloud environments due to architecture or resource differences
- **Observability is Essential**: Prometheus metrics and structured logging saved hours of debugging time
- **Idempotency Matters**: Re-runnable pipelines with proper message acknowledgment are essential for reliability
- **Documentation Pays Off**: Clear README files help teammates, instructors, and future employers understand your work
- **Version Control Everything**: Including environment files (as .sample), Dockerfiles, and infrastructure configuration

### What I Would Improve Given More Time

- **Automated Testing**: Write unit tests for each component and integration tests for the full pipeline
- **CI/CD Pipeline**: Implement GitHub Actions for automated builds, tests, and deployments
- **Infrastructure as Code**: Use Terraform or Pulumi for reproducible cloud resource provisioning
- **Data Quality Dashboard**: Build real-time data quality metrics and anomaly detection in Grafana
- **Cost Optimization**: Implement MinIO lifecycle policies to archive old data to cheaper storage tiers
- **Security Hardening**: Add authentication to all services, rotate credentials, and implement network policies

---

## ☁️ Azure Deployment

This pipeline has been successfully deployed to **Azure Virtual Machines**, demonstrating cloud readiness and production deployment capabilities.

### Azure Configuration

- **VM Type**: Standard B2s (2 vCPUs, 4GB RAM)
- **OS**: Ubuntu Server 24.04 LTS
- **Region**: West US 2
- **Networking**: Public IP with firewall rules for ports 8501, 3000, 9090, 9001
- **Storage**: Persistent volumes for DuckDB, Prometheus, Grafana, and MinIO data

### Deployment Verification

All screenshots in this README were captured from the Azure VM deployment, proving:
- ✅ Identical behavior between local and cloud environments
- ✅ Proper Docker networking and volume mounts
- ✅ Correct firewall and port configuration
- ✅ Data persistence across container restarts
- ✅ Production-grade monitoring and observability

The pipeline successfully completed two full backfill runs on Azure, demonstrating reliability and stability in a cloud environment.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Contact

**Fletcher Newman**
- **GitHub**: [@fletcher-newman](https://github.com/fletcher-newman)
- **Email**: fletcht13@gmail.com

---

**Built with ❤️ as part of Pipeline Engineering coursework at Texas A&M University**

*This project demonstrates practical skills in data engineering, distributed systems, machine learning, and cloud deployment that are directly applicable to industry roles.*
