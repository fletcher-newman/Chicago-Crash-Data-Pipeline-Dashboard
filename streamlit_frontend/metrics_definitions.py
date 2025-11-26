# metrics_definitions.py
"""
Prometheus metrics definitions for Streamlit app.
This module is imported by both the metrics server and the Streamlit app
to ensure they share the same registry.

In multiprocess mode, Gauge metrics need to specify how they should be aggregated:
- 'liveall': All live processes report their values (default)
- 'livesum': Sum across all processes
- 'max': Maximum value across all processes
- 'min': Minimum value across all processes
"""

from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------
# Prometheus Metrics
# ---------------------------------

# Service uptime
streamlit_uptime = Gauge(
    'streamlit_uptime_seconds',
    'Time in seconds since the Streamlit app started',
    multiprocess_mode='liveall'
)

# Model quality metrics (populated from metadata)
# Use 'liveall' mode - these values should be the same across all processes
model_accuracy = Gauge(
    'streamlit_model_accuracy',
    'Model accuracy metric',
    multiprocess_mode='liveall'
)

model_precision = Gauge(
    'streamlit_model_precision',
    'Model precision metric',
    multiprocess_mode='liveall'
)

model_recall = Gauge(
    'streamlit_model_recall',
    'Model recall metric',
    multiprocess_mode='liveall'
)

model_f1_score = Gauge(
    'streamlit_model_f1_score',
    'Model F1 score metric',
    multiprocess_mode='liveall'
)

# Prediction metrics
predictions_total = Counter(
    'streamlit_predictions_total',
    'Total number of predictions made'
)

prediction_latency_seconds = Histogram(
    'streamlit_prediction_latency_seconds',
    'Time taken to make predictions',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
)

# Data access metrics
db_queries_total = Counter(
    'streamlit_db_queries_total',
    'Total number of database queries executed'
)

rows_loaded_total = Counter(
    'streamlit_rows_loaded_total',
    'Total number of rows loaded from database'
)

# Model loading metrics
model_load_duration_seconds = Histogram(
    'streamlit_model_load_duration_seconds',
    'Time taken to load the model',
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# User interaction metrics
tab_views_total = Counter(
    'streamlit_tab_views_total',
    'Total number of tab views',
    ['tab_name']
)

page_loads_total = Counter(
    'streamlit_page_loads_total',
    'Total number of page loads/refreshes'
)
