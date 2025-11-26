import streamlit as st
import requests
import json
from datetime import datetime
import plotly.express as px
import pandas as pd
import duckdb
from scheduler_tab import scheduler_tab
# import pickle
import joblib
import xgboost
import time
import sys
import os
from threading import Thread

# Prometheus multiprocess mode setup (must be done before importing metrics)
# The PROMETHEUS_MULTIPROC_DIR environment variable is set in the Dockerfile startup script
if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
    print(f"[Streamlit] Using Prometheus multiprocess mode: {os.environ['PROMETHEUS_MULTIPROC_DIR']}")

# Prometheus metrics
from prometheus_client import start_http_server

# Import metrics definitions (shared with metrics server)
from metrics_definitions import (
    streamlit_uptime,
    model_accuracy,
    model_precision,
    model_recall,
    model_f1_score,
    predictions_total,
    prediction_latency_seconds,
    db_queries_total,
    rows_loaded_total,
    model_load_duration_seconds,
    tab_views_total,
    page_loads_total
)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Model artifact paths
MODEL_ARTIFACT_PATH = "artifacts/model.pkl"
MODEL_METADATA_PATH = "artifacts/model_metadata.json"

# Page configuration (must be first st command)
st.set_page_config(
    page_title="Chicago Crash ETL Dashboard",
    # page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def start_uptime_tracking():
    """Start uptime tracking thread (cached to run only once)"""
    start_time = time.time()
    def update_uptime():
        while True:
            streamlit_uptime.set(time.time() - start_time)
            time.sleep(10)

    uptime_thread = Thread(target=update_uptime, daemon=True)
    uptime_thread.start()
    return True

# Initialize uptime tracking
_ = start_uptime_tracking()

@st.cache_resource
def load_model(model_path: str):
    """
    Load the trained ML model from a pickle file.

    Args:
        model_path: Path to the .pkl model file

    Returns:
        The loaded model object, or None if loading fails
    """
    start = time.time()
    try:
        import sklearn.compose
        import sklearn.preprocessing
        import sklearn.pipeline
        # with open(model_path, 'rb') as f:
        #     model = pickle.load(f)
        model = joblib.load(model_path)

        # Track model load duration
        model_load_duration_seconds.observe(time.time() - start)
        return model
    except FileNotFoundError:
        st.error(f"❌ Model file not found at: {model_path}")
        st.info("Please ensure the model file exists in the artifacts folder.")
        return None
    except Exception as e:
        st.error(f"❌ Failed to load model: {str(e)}")
        return None

@st.cache_data
def load_model_metadata(metadata_path: str):
    """
    Load model metadata from JSON file.

    Args:
        metadata_path: Path to the model_metadata.json file

    Returns:
        Dictionary containing model metadata, or None if loading fails
    """
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return metadata
    except FileNotFoundError:
        st.error(f"❌ Model metadata file not found at: {metadata_path}")
        st.info("Please ensure the metadata file exists in the artifacts folder.")
        return None
    except Exception as e:
        st.error(f"❌ Failed to load model metadata: {str(e)}")
        return None

def update_model_metrics(metadata):
    """
    Update Prometheus metrics from model metadata.
    This function is NOT cached so metrics update on every call.

    Args:
        metadata: Dictionary containing model metadata
    """
    if metadata and 'test_metrics' in metadata:
        test_metrics = metadata['test_metrics']
        # Handle different field name variations in metadata
        if 'accuracy' in test_metrics:
            model_accuracy.set(test_metrics['accuracy'])
        if 'precision' in test_metrics:
            model_precision.set(test_metrics['precision'])
        # Handle 'recall' or 'recal' (typo in metadata)
        if 'recall' in test_metrics:
            model_recall.set(test_metrics['recall'])
        elif 'recal' in test_metrics:
            model_recall.set(test_metrics['recal'])
        # Handle 'f1_score' or 'f1'
        if 'f1_score' in test_metrics:
            model_f1_score.set(test_metrics['f1_score'])
        elif 'f1' in test_metrics:
            model_f1_score.set(test_metrics['f1'])

def get_duckdb_connection(db_path: str, read_only: bool = True):
    """
    Get a DuckDB connection.

    Note: Creates a fresh connection each time. DuckDB is fast enough that
    caching is not needed and can cause "Connection already closed" errors.

    Args:
        db_path: Path to the DuckDB database file
        read_only: Whether to open in read-only mode (default: True)

    Returns:
        DuckDB connection object, or None if connection fails
    """
    try:
        if not os.path.exists(db_path):
            st.warning(f"⚠️ Database file not found at: {db_path}")
            return None

        conn = duckdb.connect(db_path, read_only=read_only)
        return conn
    except Exception as e:
        st.error(f"❌ Failed to connect to DuckDB: {str(e)}")
        return None

def check_container_health(service_name: str) -> dict:
    """Check container health by attempting to connect to their ports."""
    import socket

    # Map service names to their Docker hostnames and ports
    service_config = {
        "minio": ("minio", 9000),
        "rabbitmq": ("rabbitmq", 5672),
        "extractor": ("extractor", None),
        "transformer": ("transformer", None),
        "cleaner": ("cleaner", None)
    }

    if service_name not in service_config:
        return {"status": "down", "message": "Unknown"}

    hostname, port = service_config[service_name]

    if port:
        # Services with ports - try to connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((hostname, port))
            sock.close()

            if result == 0:
                return {"status": "running", "message": "✅ Running"}
            else:
                return {"status": "down", "message": "❌ Down"}
        except Exception:
            return {"status": "down", "message": "❌ Unreachable"}
    else:
        # Services without exposed ports - assume running if in Docker network
        return {"status": "running", "message": "✅ Running"}

def render_status_card(service_name: str, display_name: str):
    health = check_container_health(service_name)
    if health["status"] == "running":
        st.success(f"**{display_name}**\n\n{health['message']}")
    else:
        st.error(f"**{display_name}**\n\n{health['message']}")

def render_home_tab():
    st.title("Chicago Crash ETL Dashboard")
    st.markdown("---")
    
    st.header("ML Pipeline Overview")
    st.markdown("This dashboard manages the end-to-end ETL pipeline for Chicago crash data.")
    
    with st.expander("Hit and Run Prediction Pipeline", expanded=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            #### Hit and Run Detection
            **Label predicted:** `hit_and_run_i` • **Type:** binary • **Positive class:** 1
            
            **Pipeline:** Predict hit-and-run crashes using time, location, weather, and circumstances.
            
            **Key features:**
            - `crash_hour` & `is_weekend` — Late night/weekend patterns
            - `lighting_condition` — Darkness increases likelihood
            - `intersection_related_i` — Location type correlation
            - `weather_condition` — Poor visibility effects
            - `grid_id` — Geographic patterns
            """)
        with col2:
            st.markdown("""
            **Class imbalance:**
            - Positives: ~35%
            - Negatives: ~65%
            - Handling: class_weight balanced
            
            **Data grain:** One row = one crash
            
            **Gold table:** gold.crashes
            """)
    
    st.markdown("---")
    st.header("Container Health Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_status_card("minio", "MinIO")
    with col2:
        render_status_card("rabbitmq", "RabbitMQ")
    with col3:
        render_status_card("extractor", "Extractor")
    with col4:
        render_status_card("transformer", "Transformer")
    with col5:
        render_status_card("cleaner", "Cleaner")
    
    if st.button("Refresh Health Status"):
        st.rerun()


def render_data_management_tab():
    """Render the Data Management tab for MinIO and DuckDB management."""
    from minio import Minio
    from minio.error import S3Error
    import duckdb

    st.title("🧰 Data Management")
    st.markdown("Centralized admin for storage and warehouse housekeeping")
    st.markdown("---")

    # =============================================================================
    # A) MinIO Browser & Delete
    # =============================================================================
    st.header("📦 MinIO Object Storage Management")

    # MinIO connection helper
    def get_minio_client():
        """Get MinIO client connection."""
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        minio_user = os.getenv("MINIO_USER", "admin")
        minio_pass = os.getenv("MINIO_PASS", "admin123")

        return Minio(
            minio_endpoint,
            access_key=minio_user,
            secret_key=minio_pass,
            secure=False
        )

    # Create two columns for MinIO operations
    col1, col2 = st.columns(2)

    # =========================================================================
    # Section 1: Delete by Folder (Prefix)
    # =========================================================================
    with col1:
        st.subheader("🗂️ Delete by Folder (Prefix)")

        bucket_folder = st.selectbox(
            "Select Bucket",
            ["raw-data", "transform-data"],
            key="folder_bucket"
        )

        prefix_input = st.text_input(
            "Prefix (folder path)",
            placeholder="crash/corr=2025-10-14-00-26-56/",
            help="Example: crash/corr=2025-10-14-00-26-56/",
            key="prefix_input"
        )

        # Preview button
        if st.button("🔍 Preview Objects", key="preview_folder"):
            if prefix_input:
                try:
                    client = get_minio_client()
                    objects = list(client.list_objects(bucket_folder, prefix=prefix_input, recursive=True))

                    if objects:
                        st.success(f"Found {len(objects)} object(s)")

                        # Show first 10 objects
                        with st.expander("Preview (first 10 objects)", expanded=True):
                            for idx, obj in enumerate(objects[:10]):
                                st.text(f"{idx+1}. {obj.object_name} ({obj.size} bytes)")
                            if len(objects) > 10:
                                st.info(f"...and {len(objects)-10} more")

                        # Store in session state for deletion
                        st.session_state['preview_objects'] = objects
                        st.session_state['preview_bucket'] = bucket_folder
                    else:
                        st.warning("No objects found with this prefix")
                        st.session_state['preview_objects'] = []

                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a prefix")

        # Confirmation checkbox
        confirm_folder = st.checkbox("✅ I confirm deletion", key="confirm_folder")

        # Delete button (disabled unless preview run and confirmed)
        delete_folder_disabled = not (confirm_folder and 'preview_objects' in st.session_state and st.session_state.get('preview_objects'))

        if st.button("🗑️ Delete Folder", disabled=delete_folder_disabled, key="delete_folder_btn", type="primary"):
            try:
                client = get_minio_client()
                objects = st.session_state.get('preview_objects', [])
                bucket = st.session_state.get('preview_bucket')

                deleted_count = 0
                for obj in objects:
                    client.remove_object(bucket, obj.object_name)
                    deleted_count += 1

                st.success(f"✅ Deleted {deleted_count} object(s) from {bucket}/{prefix_input}")

                # Clear session state
                del st.session_state['preview_objects']
                del st.session_state['preview_bucket']

            except Exception as e:
                st.error(f"Error during deletion: {str(e)}")

    # =========================================================================
    # Section 2: Delete by Bucket
    # =========================================================================
    with col2:
        st.subheader("🪣 Delete Entire Bucket")
        st.warning("⚠️ This will delete ALL objects in the bucket!")

        bucket_delete = st.selectbox(
            "Select Bucket to Delete",
            ["raw-data", "transform-data"],
            key="bucket_delete"
        )

        confirm_bucket = st.checkbox("✅ I confirm bucket deletion", key="confirm_bucket")

        if st.button("🗑️ Delete Bucket", disabled=not confirm_bucket, key="delete_bucket_btn", type="primary"):
            try:
                client = get_minio_client()

                # First, delete all objects
                objects = list(client.list_objects(bucket_delete, recursive=True))
                deleted_count = 0

                with st.spinner(f"Deleting {len(objects)} objects..."):
                    for obj in objects:
                        client.remove_object(bucket_delete, obj.object_name)
                        deleted_count += 1

                st.success(f"✅ Deleted {deleted_count} object(s) from bucket '{bucket_delete}'")
                st.info("Note: Bucket structure is preserved (will be recreated on next write)")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.markdown("---")

    # =============================================================================
    # B) Gold Admin (DuckDB)
    # =============================================================================
    st.header("💎 Gold Database (DuckDB) Management")

    gold_db_path = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📊 Database Status")

        try:
            # Check if DB file exists and get stats
            if os.path.exists(gold_db_path):
                conn = get_duckdb_connection(gold_db_path, read_only=True)
                if conn is None:
                    return

                try:
                    # Get current database/catalog name
                    current_db = conn.execute("SELECT current_database()").fetchone()[0]

                    # Get table list from gold schema
                    tables = conn.execute(f"""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'gold' AND table_catalog = '{current_db}'
                    """).fetchall()

                    # Display status card
                    st.info(f"**Database Path:** `{gold_db_path}` (catalog: `{current_db}`)")

                    if tables:
                        st.success(f"**Tables:** {len(tables)}")

                        # Show row counts per table (using full path)
                        for table in tables:
                            table_name = table[0]
                            row_count = conn.execute(f"SELECT COUNT(*) FROM {current_db}.gold.{table_name}").fetchone()[0]
                            st.metric(f"📋 {table_name}", f"{row_count:,} rows")
                    else:
                        st.warning("Database exists but contains no tables")
                finally:
                    conn.close()
            else:
                st.error("❌ Gold database file not found")

        except Exception as e:
            st.error(f"Error reading database: {str(e)}")

    with col2:
        st.subheader("🗑️ Reset Database")

        confirm_wipe = st.checkbox("✅ I confirm wiping Gold DB", key="confirm_wipe")

        if st.button("🗑️ Wipe Gold DB (ENTIRE FILE)", disabled=not confirm_wipe, type="primary", key="wipe_gold"):
            try:
                if os.path.exists(gold_db_path):
                    os.remove(gold_db_path)
                    st.success("✅ Gold database wiped successfully!")
                    st.info("Database will be recreated on next cleaner run")
                    st.rerun()
                else:
                    st.warning("Database file doesn't exist")
            except Exception as e:
                st.error(f"Error wiping database: {str(e)}")

    st.markdown("---")

    # =============================================================================
    # C) Quick Peek (Gold Sanity View)
    # =============================================================================
    st.header("👀 Quick Peek - Gold Data Sample")
    st.markdown("Light sanity check of cleaned data (not full EDA)")

    try:
        if os.path.exists(gold_db_path):
            conn = get_duckdb_connection(gold_db_path, read_only=True)
            if conn is None:
                return

            try:
                # Get current database/catalog name
                current_db = conn.execute("SELECT current_database()").fetchone()[0]

                # Get tables from gold schema
                tables = conn.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'gold' AND table_catalog = '{current_db}'
                """).fetchall()

                if tables:
                    # Get first table (crashes)
                    table_name = tables[0][0]
                    full_table_path = f"{current_db}.gold.{table_name}"

                    # Get all columns
                    columns_result = conn.execute(f"DESCRIBE {full_table_path}").fetchall()
                    all_columns = [col[0] for col in columns_result]

                    col1, col2 = st.columns(2)

                    with col1:
                        # Column selection
                        selected_columns = st.multiselect(
                            "Select Columns to Preview",
                            all_columns,
                            default=all_columns[:8] if len(all_columns) >= 8 else all_columns,
                            help="If empty, will auto-select first 8 columns"
                        )

                    with col2:
                        # Row limit slider
                        row_limit = st.slider(
                            "Number of Rows",
                            min_value=10,
                            max_value=200,
                            value=50,
                            step=10
                        )

                    if st.button("🔍 Preview Data", key="preview_gold"):
                        # Use selected columns or default to first 8
                        cols_to_show = selected_columns if selected_columns else all_columns[:8]
                        cols_str = ", ".join(cols_to_show)

                        # Query data using full table path
                        query = f"SELECT {cols_str} FROM {full_table_path} LIMIT {row_limit}"
                        df = conn.execute(query).fetchdf()

                        st.success(f"Showing {len(df)} rows from `{table_name}`")
                        st.dataframe(df, use_container_width=True)

                        # Show column types
                        with st.expander("📋 Column Types"):
                            for col in columns_result:
                                if col[0] in cols_to_show:
                                    st.text(f"{col[0]}: {col[1]}")
                else:
                    st.warning("No tables found in Gold database")
            finally:
                conn.close()
        else:
            st.warning("Gold database file not found. Run the cleaner first.")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_data_fetcher_tab():
    """Render the Data Fetcher tab with Streaming and Backfill subtabs."""
    st.header("🔍 Data Fetcher")
    st.markdown("Fetch crash data from Chicago Open Data Portal")

    # Create subtabs
    subtab1, subtab2 = st.tabs(["📡 Streaming", "🕰️ Backfill"])

    # =============================================================================
    # Streaming Subtab
    # =============================================================================
    with subtab1:
        st.subheader("📡 Streaming Mode")
        st.markdown("Fetch **recent** crash data (last N days)")

        # Auto-generate correlation ID
        corr_id = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        st.text_input("Correlation ID (auto-generated)", value=corr_id, disabled=True, key="stream_corr_id")

        # Since days input
        since_days = st.number_input(
            "Since Days",
            min_value=1,
            max_value=365,
            value=30,
            help="Fetch crashes from the last N days"
        )

        st.markdown("---")
        st.markdown("### 🔧 Enrichment Options")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🚗 Vehicles Dataset")
            include_vehicles = st.checkbox("Include Vehicles", value=True, key="stream_inc_vehicles")

            if include_vehicles:
                select_all_vehicles = st.checkbox("Select all vehicle columns", value=False, key="stream_sel_all_veh")

                # Default vehicle columns from streaming.json
                default_vehicle_cols = [
                    "crash_record_id", "unit_no", "vehicle_id", "unit_type", "make",
                    "model", "vehicle_year", "travel_direction", "maneuver",
                    "first_contact_point", "vehicle_defect", "vehicle_use", "towed_i"
                ]

                vehicle_columns = st.multiselect(
                    "Vehicle columns to fetch",
                    options=default_vehicle_cols,
                    default=default_vehicle_cols if select_all_vehicles else ["crash_record_id", "make", "vehicle_year", "travel_direction", "maneuver"],
                    key="stream_veh_cols"
                )

        with col2:
            st.markdown("#### 👥 People Dataset")
            include_people = st.checkbox("Include People", value=True, key="stream_inc_people")

            if include_people:
                select_all_people = st.checkbox("Select all people columns", value=False, key="stream_sel_all_ppl")

                # Default people columns from streaming.json
                default_people_cols = [
                    "crash_record_id", "person_id", "person_type", "age", "sex",
                    "seat_no", "injury_classification", "safety_equipment",
                    "airbag_deployed", "ejection"
                ]

                people_columns = st.multiselect(
                    "People columns to fetch",
                    options=default_people_cols,
                    default=default_people_cols if select_all_people else ["crash_record_id", "person_type", "age", "sex", "injury_classification"],
                    key="stream_ppl_cols"
                )

        st.markdown("---")

        # Build the request payload
        streaming_payload = {
            "mode": "streaming",
            "source": "crash",
            "join_key": "crash_record_id",
            "corr_id": corr_id,
            "primary": {
                "id": "85ca-t3if",
                "alias": "crashes",
                "select": "crash_record_id,crash_date,crash_type,posted_speed_limit,weather_condition,lane_cnt,hit_and_run_i,beat_of_occurrence,num_units,injuries_total,crash_hour,crash_day_of_week,latitude,longitude,traffic_control_device,work_zone_i,work_zone_type,private_property_i,lighting_condition,road_defect,roadway_surface_cond,street_direction,trafficway_type,intersection_related_i",
                "where_by": {"since_days": since_days},
                "order": "crash_date, crash_record_id",
                "page_size": 2000
            },
            "enrich": [],
            "batching": {
                "id_batch_size": 50,
                "max_workers": {"vehicles": 4, "people": 4}
            },
            "storage": {
                "bucket": "raw-data",
                "prefix": "crash",
                "compress": True
            }
        }

        # Add enrichment datasets if selected
        if include_vehicles and vehicle_columns:
            streaming_payload["enrich"].append({
                "id": "68nd-jvt3",
                "alias": "vehicles",
                "select": ",".join(vehicle_columns)
            })

        if include_people and people_columns:
            streaming_payload["enrich"].append({
                "id": "u6pd-qa9d",
                "alias": "people",
                "select": ",".join(people_columns)
            })

        # Preview JSON
        with st.expander("🔍 Preview Request JSON"):
            st.json(streaming_payload)

        # Action buttons
        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("📤 Publish to RabbitMQ", key="stream_publish", type="primary"):
                try:
                    import pika

                    # Connect to RabbitMQ
                    connection = pika.BlockingConnection(
                        pika.ConnectionParameters(host='rabbitmq', port=5672)
                    )
                    channel = connection.channel()
                    channel.queue_declare(queue='extract', durable=True)

                    # Publish message
                    import json
                    channel.basic_publish(
                        exchange='',
                        routing_key='extract',
                        body=json.dumps(streaming_payload),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )

                    connection.close()
                    st.success(f"✅ Job queued successfully! Corr ID: `{corr_id}`")

                except Exception as e:
                    st.error(f"❌ Failed to publish: {str(e)}")

        with col2:
            if st.button("🔄 Reset Form", key="stream_reset"):
                st.rerun()

    # =============================================================================
    # Backfill Subtab
    # =============================================================================
    with subtab2:
        st.subheader("🕰️ Backfill Mode")
        st.markdown("Fetch data for a **historical date/time range**")

        # Auto-generate correlation ID
        corr_id_backfill = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        st.text_input("Correlation ID (auto-generated)", value=corr_id_backfill, disabled=True, key="backfill_corr_id")

        # Date and time range inputs
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Start")
            start_date = st.date_input("Start Date", value=datetime(2020, 1, 1), key="backfill_start_date")
            start_time = st.time_input("Start Time", value=datetime.strptime("00:00:00", "%H:%M:%S").time(), key="backfill_start_time")

        with col2:
            st.markdown("#### End")
            end_date = st.date_input("End Date", value=datetime(2020, 1, 2), key="backfill_end_date")
            end_time = st.time_input("End Time", value=datetime.strptime("00:00:00", "%H:%M:%S").time(), key="backfill_end_time")

        st.markdown("---")
        st.markdown("### 🔧 Enrichment Options")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🚗 Vehicles Dataset")
            include_vehicles_bf = st.checkbox("Include Vehicles", value=True, key="backfill_inc_vehicles")

            if include_vehicles_bf:
                select_all_vehicles_bf = st.checkbox("Select all vehicle columns", value=False, key="backfill_sel_all_veh")

                default_vehicle_cols_bf = [
                    "crash_record_id", "make", "vehicle_year", "travel_direction", "maneuver"
                ]

                vehicle_columns_bf = st.multiselect(
                    "Vehicle columns to fetch",
                    options=default_vehicle_cols_bf,
                    default=default_vehicle_cols_bf if select_all_vehicles_bf else default_vehicle_cols_bf,
                    key="backfill_veh_cols"
                )

        with col2:
            st.markdown("#### 👥 People Dataset")
            include_people_bf = st.checkbox("Include People", value=True, key="backfill_inc_people")

            if include_people_bf:
                select_all_people_bf = st.checkbox("Select all people columns", value=False, key="backfill_sel_all_ppl")

                default_people_cols_bf = [
                    "crash_record_id", "person_type", "age", "sex", "injury_classification", "seat_no", "airbag_deployed"
                ]

                people_columns_bf = st.multiselect(
                    "People columns to fetch",
                    options=default_people_cols_bf,
                    default=default_people_cols_bf if select_all_people_bf else default_people_cols_bf,
                    key="backfill_ppl_cols"
                )

        st.markdown("---")

        # Combine date and time
        start_datetime = datetime.combine(start_date, start_time).isoformat()
        end_datetime = datetime.combine(end_date, end_time).isoformat()

        # Build the request payload
        backfill_payload = {
            "mode": "backfill",
            "source": "crash",
            "join_key": "crash_record_id",
            "corr_id": corr_id_backfill,
            "date_range": {
                "field": "crash_date",
                "start": start_datetime,
                "end": end_datetime
            },
            "primary": {
                "id": "85ca-t3if",
                "alias": "crashes",
                "select": "crash_record_id,crash_date,crash_type,posted_speed_limit,weather_condition,lane_cnt,hit_and_run_i,beat_of_occurrence,num_units,injuries_total,crash_hour,crash_day_of_week,latitude,longitude,traffic_control_device,work_zone_i,work_zone_type,private_property_i,lighting_condition,road_defect,roadway_surface_cond,street_direction,trafficway_type,intersection_related_i",
                "order": "crash_date, crash_record_id",
                "page_size": 2000
            },
            "enrich": [],
            "batching": {
                "id_batch_size": 50,
                "max_workers": {"vehicles": 4, "people": 4}
            },
            "storage": {
                "bucket": "raw-data",
                "prefix": "crash",
                "compress": True
            }
        }

        # Add enrichment datasets if selected
        if include_vehicles_bf and vehicle_columns_bf:
            backfill_payload["enrich"].append({
                "id": "68nd-jvt3",
                "alias": "vehicles",
                "select": ",".join(vehicle_columns_bf)
            })

        if include_people_bf and people_columns_bf:
            backfill_payload["enrich"].append({
                "id": "u6pd-qa9d",
                "alias": "people",
                "select": ",".join(people_columns_bf)
            })

        # Preview JSON
        with st.expander("🔍 Preview Request JSON"):
            st.json(backfill_payload)

        # Action buttons
        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("📤 Publish to RabbitMQ", key="backfill_publish", type="primary"):
                try:
                    import pika

                    # Connect to RabbitMQ
                    connection = pika.BlockingConnection(
                        pika.ConnectionParameters(host='rabbitmq', port=5672)
                    )
                    channel = connection.channel()
                    channel.queue_declare(queue='extract', durable=True)

                    # Publish message
                    import json
                    channel.basic_publish(
                        exchange='',
                        routing_key='extract',
                        body=json.dumps(backfill_payload),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )

                    connection.close()
                    st.success(f"✅ Job queued successfully! Corr ID: `{corr_id_backfill}`")

                except Exception as e:
                    st.error(f"❌ Failed to publish: {str(e)}")

        with col2:
            if st.button("🔄 Reset Form", key="backfill_reset"):
                st.rerun()


def render_eda_tab():
    """Render the EDA tab with exploratory data analysis and visualizations."""
    st.header("📊 Exploratory Data Analysis (EDA)")
    st.markdown("Analyze cleaned crash data from the Gold database")

    gold_db_path = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb")

    if not os.path.exists(gold_db_path):
        st.error("❌ Gold database not found. Please run the data pipeline first.")
        return

    try:
        conn = get_duckdb_connection(gold_db_path, read_only=True)
        if conn is None:
            return

        try:
            # Get current database/catalog name
            current_db = conn.execute("SELECT current_database()").fetchone()[0]

            # Check if crashes table exists
            tables = conn.execute(f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'gold' AND table_catalog = '{current_db}'
            """).fetchall()

            if not tables:
                st.warning("⚠️ No tables found in Gold database. Run the pipeline first.")
                return

            # Load data
            full_table_path = f"{current_db}.gold.crashes"
            df = conn.execute(f"SELECT * FROM {full_table_path}").fetchdf()
        finally:
            conn.close()

        if df.empty:
            st.warning("⚠️ Gold database is empty. Run the pipeline first.")
            return

        # =============================================================================
        # 1. Summary Statistics
        # =============================================================================
        st.subheader("📈 Summary Statistics")

        # Quick metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Crashes", f"{len(df):,}")

        with col2:
            missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100)
            st.metric("Missing Values %", f"{missing_pct:.2f}%")

        with col3:
            hit_run_count = df['hit_and_run_i'].sum() if 'hit_and_run_i' in df.columns else 0
            st.metric("Hit & Run Crashes", f"{int(hit_run_count):,}")

        with col4:
            if 'hit_and_run_i' in df.columns:
                hit_run_rate = (df['hit_and_run_i'].sum() / len(df) * 100)
                st.metric("Hit & Run Rate", f"{hit_run_rate:.2f}%")

        st.markdown("---")

        # Detailed statistics in expandable sections
        col1, col2 = st.columns(2)

        with col1:
            with st.expander("📊 Numeric Column Statistics", expanded=False):
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                numeric_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude']]

                if len(numeric_cols) > 0:
                    stats_data = []
                    for col in numeric_cols[:10]:  # Limit to first 10 numeric columns
                        stats_data.append({
                            'Column': col,
                            'Min': f"{df[col].min():.2f}",
                            'Max': f"{df[col].max():.2f}",
                            'Mean': f"{df[col].mean():.2f}",
                            'Missing': f"{df[col].isnull().sum()} ({df[col].isnull().sum()/len(df)*100:.1f}%)"
                        })

                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No numeric columns to display")

        with col2:
            with st.expander("📋 Categorical Column Statistics", expanded=False):
                categorical_cols = df.drop(columns=['crash_record_id']).select_dtypes(include=['object']).columns

                if len(categorical_cols) > 0:
                    for col in categorical_cols[:8]:  # Limit to first 8 categorical columns
                        st.markdown(f"**{col}**")
                        top_categories = df[col].value_counts().head(5)

                        cat_data = []
                        for category, count in top_categories.items():
                            pct = (count / len(df) * 100)
                            cat_data.append(f"- `{category}`: {count:,} ({pct:.1f}%)")

                        st.markdown("\n".join(cat_data))
                        st.markdown("")
                else:
                    st.info("No categorical columns to display")

        st.markdown("---")

        # =============================================================================
        # 2. Visualizations
        # =============================================================================
        st.subheader("📊 Visualizations")

        # Create tabs for different visualization categories
        viz_tabs = st.tabs([
            "Speed & Hit & Run",
            "Weather & Lighting",
            "Temporal Patterns",
            "Location & Conditions",
            "Advanced Hit & Run"
        ])

        # -------------------------------------------------------------------------
        # Tab 1: Speed & Hit & Run Analysis
        # -------------------------------------------------------------------------
        with viz_tabs[0]:
            st.markdown("### Posted Speed Limit & Hit & Run")

            if 'posted_speed_limit' in df.columns and 'hit_and_run_i' in df.columns:
                # 1. Histogram: Speed by Hit & Run (overlay)
                df_temp = df.copy()
                df_temp['Hit & Run'] = df_temp['hit_and_run_i'].map({0: 'No', 1: 'Yes'})

                fig = px.histogram(
                    df_temp,
                    x='posted_speed_limit',
                    color='Hit & Run',
                    title='Posted Speed Limit: Hit & Run vs Non Hit & Run',
                    nbins=20,
                    barmode='overlay',
                    opacity=0.7,
                    color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}
                )
                st.plotly_chart(fig, use_container_width=True)

                # 2. Box plot: Speed Limit by Hit & Run
                fig = px.box(
                    df_temp,
                    x='Hit & Run',
                    y='posted_speed_limit',
                    title='Speed Limit Distribution by Hit & Run Status',
                    color='Hit & Run',
                    color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}
                )
                st.plotly_chart(fig, use_container_width=True)

                # 3. Hit & Run Rate by Speed Limit Bins
                df_temp['speed_bin'] = pd.cut(df_temp['posted_speed_limit'],
                                               bins=[0, 20, 30, 40, 50, 100],
                                               labels=['0-20', '21-30', '31-40', '41-50', '50+'])

                speed_stats = df_temp.groupby('speed_bin').agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                speed_stats.columns = ['speed_bin', 'hit_run_count', 'total_count']
                speed_stats['hit_run_rate'] = speed_stats['hit_run_count'] / speed_stats['total_count'] * 100

                fig = px.bar(
                    speed_stats,
                    x='speed_bin',
                    y='hit_run_rate',
                    title='Hit & Run Rate by Speed Limit Range (%)',
                    color='hit_run_rate',
                    color_continuous_scale='Reds',
                    labels={'speed_bin': 'Speed Limit (mph)', 'hit_run_rate': 'Hit & Run Rate (%)'}
                )
                st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------------
        # Tab 2: Weather & Lighting Conditions
        # -------------------------------------------------------------------------
        with viz_tabs[1]:
            st.markdown("### Weather Conditions & Hit & Run")

            if 'weather_condition' in df.columns and 'hit_and_run_i' in df.columns:
                # 4. Hit & Run Rate by Weather
                weather_stats = df.groupby('weather_condition').agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                weather_stats.columns = ['weather_condition', 'hit_run_count', 'total_count']
                weather_stats['hit_run_rate'] = weather_stats['hit_run_count'] / weather_stats['total_count'] * 100

                fig = px.bar(
                    weather_stats,
                    x='weather_condition',
                    y='hit_run_rate',
                    title='Hit & Run Rate by Weather Condition (%)',
                    color='hit_run_rate',
                    color_continuous_scale='Reds'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

                # 5. Hit & Run Count by Weather (stacked)
                df_temp = df.copy()
                df_temp['Hit & Run'] = df_temp['hit_and_run_i'].map({0: 'No', 1: 'Yes'})

                weather_hr = df_temp.groupby(['weather_condition', 'Hit & Run']).size().reset_index(name='count')
                fig = px.bar(
                    weather_hr,
                    x='weather_condition',
                    y='count',
                    color='Hit & Run',
                    title='Crash Distribution by Weather: Hit & Run vs Non Hit & Run',
                    barmode='stack',
                    color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Lighting Conditions & Hit & Run")

            if 'lighting_condition' in df.columns and 'hit_and_run_i' in df.columns:
                # 6. Hit & Run Rate by Lighting Condition
                lighting_stats = df.groupby('lighting_condition').agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                lighting_stats.columns = ['lighting_condition', 'hit_run_count', 'total_count']
                lighting_stats['hit_run_rate'] = lighting_stats['hit_run_count'] / lighting_stats['total_count'] * 100

                fig = px.bar(
                    lighting_stats,
                    x='lighting_condition',
                    y='hit_run_rate',
                    title='Hit & Run Rate by Lighting Condition (%)',
                    color='hit_run_rate',
                    color_continuous_scale='Reds'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------------
        # Tab 3: Temporal Patterns
        # -------------------------------------------------------------------------
        with viz_tabs[2]:
            st.markdown("### Hourly and Daily Patterns")

            if 'crash_hour' in df.columns and 'hit_and_run_i' in df.columns:
                # 7. Line chart: Total Crashes vs Hit & Run by Hour
                df_temp = df.copy()
                hourly_total = df_temp.groupby('crash_hour').size().reset_index(name='Total Crashes')
                hourly_hr = df_temp[df_temp['hit_and_run_i'] == 1].groupby('crash_hour').size().reset_index(name='Hit & Run')

                hourly_combined = hourly_total.merge(hourly_hr, on='crash_hour', how='left').fillna(0)

                fig = px.line(
                    hourly_combined.melt(id_vars='crash_hour', var_name='Type', value_name='count'),
                    x='crash_hour',
                    y='count',
                    color='Type',
                    title='Crash Frequency by Hour: Total vs Hit & Run',
                    markers=True,
                    color_discrete_map={'Total Crashes': '#3b82f6', 'Hit & Run': '#ef4444'}
                )
                fig.update_xaxes(title='Hour of Day')
                fig.update_yaxes(title='Number of Crashes')
                st.plotly_chart(fig, use_container_width=True)

            if 'crash_hour' in df.columns and 'hit_and_run_i' in df.columns:
                # NEW: Hit & Run Rate by Hour
                hourly_hit_run = df.groupby('crash_hour').agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                hourly_hit_run.columns = ['crash_hour', 'hit_run_count', 'total_count']
                hourly_hit_run['hit_run_rate'] = hourly_hit_run['hit_run_count'] / hourly_hit_run['total_count'] * 100

                fig = px.line(
                    hourly_hit_run,
                    x='crash_hour',
                    y='hit_run_rate',
                    title='Hit & Run Rate by Hour of Day (%)',
                    markers=True,
                    color_discrete_sequence=['#ef4444']
                )
                fig.update_xaxes(title='Hour of Day')
                fig.update_yaxes(title='Hit & Run Rate (%)')
                st.plotly_chart(fig, use_container_width=True)

            if 'crash_day_of_week' in df.columns:
                # 9. Bar chart: Crashes by Day of Week
                day_names = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
                df_temp = df.copy()
                df_temp['day_name'] = df_temp['crash_day_of_week'].map(day_names)

                daily_counts = df_temp.groupby('day_name').size().reset_index(name='count')
                # Order by day of week (only include days that exist in data)
                day_order = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                existing_days = [day for day in day_order if day in daily_counts['day_name'].values]
                if existing_days:
                    daily_counts['day_name'] = pd.Categorical(daily_counts['day_name'], categories=existing_days, ordered=True)
                    daily_counts = daily_counts.sort_values('day_name')

                    fig = px.bar(
                        daily_counts,
                        x='day_name',
                        y='count',
                        title='Crash Frequency by Day of Week',
                        color='count',
                        color_continuous_scale='Blues'
                    )
                    st.plotly_chart(fig, use_container_width=True)

            if 'crash_day_of_week' in df.columns and 'hit_and_run_i' in df.columns:
                # NEW: Hit & Run Distribution by Day of Week (Pie Chart)
                day_names = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
                df_temp = df[df['hit_and_run_i'] == 1].copy()

                if len(df_temp) > 0:
                    df_temp['day_name'] = df_temp['crash_day_of_week'].map(day_names)
                    hit_run_by_day = df_temp.groupby('day_name').size().reset_index(name='count')

                    fig = px.pie(
                        hit_run_by_day,
                        values='count',
                        names='day_name',
                        title='Hit & Run Distribution by Day of Week',
                        color_discrete_sequence=px.colors.sequential.Reds_r
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hit & run incidents in the data")

            if 'crash_hour' in df.columns and 'crash_day_of_week' in df.columns:
                # 10. Heatmap: Hour × Day of Week
                day_names = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
                df_temp = df.copy()
                df_temp['day_name'] = df_temp['crash_day_of_week'].map(day_names)

                heatmap_data = df_temp.groupby(['crash_hour', 'day_name']).size().reset_index(name='count')
                heatmap_pivot = heatmap_data.pivot(index='crash_hour', columns='day_name', values='count').fillna(0)

                # Reorder columns by day of week (only include existing days)
                day_order = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                existing_cols = [day for day in day_order if day in heatmap_pivot.columns]
                heatmap_pivot = heatmap_pivot[existing_cols]

                fig = px.imshow(
                    heatmap_pivot,
                    labels=dict(x="Day of Week", y="Hour of Day", color="Crash Count"),
                    title="Crash Count Heatmap: Hour × Day of Week",
                    color_continuous_scale='YlOrRd',
                    aspect='auto'
                )
                st.plotly_chart(fig, use_container_width=True)

            if 'crash_hour' in df.columns and 'crash_day_of_week' in df.columns and 'hit_and_run_i' in df.columns:
                # NEW: Hit & Run Rate Heatmap: Hour × Day of Week
                day_names = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
                df_temp = df.copy()
                df_temp['day_name'] = df_temp['crash_day_of_week'].map(day_names)

                # Calculate hit & run rate for each hour-day combination
                heatmap_data = df_temp.groupby(['crash_hour', 'day_name']).agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                heatmap_data.columns = ['crash_hour', 'day_name', 'hit_run_count', 'total_count']
                heatmap_data['hit_run_rate'] = (heatmap_data['hit_run_count'] / heatmap_data['total_count'] * 100)

                heatmap_pivot = heatmap_data.pivot(index='crash_hour', columns='day_name', values='hit_run_rate').fillna(0)

                # Reorder columns by day of week (only include existing days)
                day_order = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                existing_cols = [day for day in day_order if day in heatmap_pivot.columns]
                heatmap_pivot = heatmap_pivot[existing_cols]

                fig = px.imshow(
                    heatmap_pivot,
                    labels=dict(x="Day of Week", y="Hour of Day", color="Hit & Run Rate (%)"),
                    title="Hit & Run Rate Heatmap: Hour × Day of Week",
                    color_continuous_scale='Reds',
                    aspect='auto'
                )
                st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------------
        # Tab 4: Location & Conditions
        # -------------------------------------------------------------------------
        with viz_tabs[3]:
            st.markdown("### Road Conditions")

            if 'roadway_surface_cond' in df.columns:
                # 11. Bar chart: Roadway Surface Condition
                surface_counts = df['roadway_surface_cond'].value_counts().reset_index()
                surface_counts.columns = ['condition', 'count']

                fig = px.bar(
                    surface_counts.head(10),
                    x='condition',
                    y='count',
                    title='Top 10 Roadway Surface Conditions',
                    color='count',
                    color_continuous_scale='Greens'
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

            if 'trafficway_type' in df.columns:
                # 12. Pie chart: Trafficway Type
                traffic_counts = df['trafficway_type'].value_counts().reset_index()
                traffic_counts.columns = ['trafficway_type', 'count']

                fig = px.pie(
                    traffic_counts,
                    values='count',
                    names='trafficway_type',
                    title='Crash Distribution by Trafficway Type'
                )
                st.plotly_chart(fig, use_container_width=True)

            if 'latitude' in df.columns and 'longitude' in df.columns and 'hit_and_run_i' in df.columns:
                # 13. Scatter map: Hit & Run Geographic Distribution
                df_geo = df.dropna(subset=['latitude', 'longitude'])
                if len(df_geo) > 0:
                    # Create hit & run label for better visualization
                    df_geo_sample = df_geo.sample(min(5000, len(df_geo))).copy()
                    df_geo_sample['Hit & Run'] = df_geo_sample['hit_and_run_i'].map({0: 'No', 1: 'Yes'})

                    fig = px.scatter_mapbox(
                        df_geo_sample,
                        lat='latitude',
                        lon='longitude',
                        color='Hit & Run',
                        title='Geographic Distribution: Hit & Run vs Non Hit & Run (Sample)',
                        mapbox_style='open-street-map',
                        zoom=10,
                        opacity=0.7,
                        color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}  # Blue for No, Red for Yes
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Additional map: Hit & Run only
                    df_hit_run = df_geo[df_geo['hit_and_run_i'] == 1]
                    if len(df_hit_run) > 0:
                        df_hit_run_sample = df_hit_run.sample(min(2000, len(df_hit_run)))

                        fig2 = px.scatter_mapbox(
                            df_hit_run_sample,
                            lat='latitude',
                            lon='longitude',
                            title='Hit & Run Incidents Only - Geographic Hotspots',
                            mapbox_style='open-street-map',
                            zoom=10,
                            opacity=0.8,
                            color_discrete_sequence=['#dc2626']  # Bright red
                        )
                        st.plotly_chart(fig2, use_container_width=True)

        # -------------------------------------------------------------------------
        # Tab 5: Advanced Analysis
        # -------------------------------------------------------------------------
        with viz_tabs[4]:
            st.markdown("### Advanced Hit & Run Analysis")

            if 'injuries_total' in df.columns and 'hit_and_run_i' in df.columns:
                # 14. Violin plot: Injuries by Hit & Run Status
                df_temp = df.copy()
                df_temp['Hit & Run'] = df_temp['hit_and_run_i'].map({0: 'No', 1: 'Yes'})

                fig = px.violin(
                    df_temp,
                    y='injuries_total',
                    x='Hit & Run',
                    title='Injury Distribution by Hit & Run Status',
                    box=True,
                    color='Hit & Run',
                    color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}
                )
                st.plotly_chart(fig, use_container_width=True)

            if 'num_units' in df.columns and 'injuries_total' in df.columns and 'hit_and_run_i' in df.columns:
                # 15. Scatter: Num Units vs Injuries colored by Hit & Run
                df_scatter = df[df['injuries_total'] < df['injuries_total'].quantile(0.95)].copy()
                df_scatter['Hit & Run'] = df_scatter['hit_and_run_i'].map({0: 'No', 1: 'Yes'})

                fig = px.scatter(
                    df_scatter,
                    x='num_units',
                    y='injuries_total',
                    color='Hit & Run',
                    title='Number of Units vs Total Injuries by Hit & Run Status',
                    opacity=0.6,
                    color_discrete_map={'No': '#3b82f6', 'Yes': '#ef4444'}
                )
                st.plotly_chart(fig, use_container_width=True)

            if 'work_zone_i' in df.columns and 'hit_and_run_i' in df.columns:
                # NEW: Hit & Run Rate in Work Zones vs Non-Work Zones
                df_temp = df.copy()
                df_temp['Work Zone'] = df_temp['work_zone_i'].map({0: 'No', 1: 'Yes'})

                workzone_stats = df_temp.groupby('Work Zone').agg({
                    'hit_and_run_i': ['sum', 'count']
                }).reset_index()
                workzone_stats.columns = ['Work Zone', 'hit_run_count', 'total_count']
                workzone_stats['hit_run_rate'] = workzone_stats['hit_run_count'] / workzone_stats['total_count'] * 100

                fig = px.bar(
                    workzone_stats,
                    x='Work Zone',
                    y='hit_run_rate',
                    title='Hit & Run Rate: Work Zone vs Non-Work Zone (%)',
                    color='hit_run_rate',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)

            # 16. Correlation heatmap for numeric columns
            st.markdown("### Correlation Matrix")
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            numeric_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude']]

            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()

                fig = px.imshow(
                    corr_matrix,
                    labels=dict(color="Correlation"),
                    title="Correlation Matrix of Numeric Features",
                    color_continuous_scale='RdBu_r',
                    aspect='auto'
                )
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")


def render_reports_tab():
    """Render the Reports tab for ETL pipeline health and metrics."""
    st.header("📑 Pipeline Reports")
    st.markdown("ETL pipeline health, run history, and data quality metrics")

    # =============================================================================
    # Summary Cards
    # =============================================================================
    st.subheader("📊 Summary Cards")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Get Gold database stats
    gold_db_path = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb")
    gold_row_count = 0
    latest_corr_id = "N/A"
    latest_data_date = "N/A"
    last_run_timestamp = "N/A"

    try:
        if os.path.exists(gold_db_path):
            conn = get_duckdb_connection(gold_db_path, read_only=True)
            if conn is not None:
                try:
                    current_db = conn.execute("SELECT current_database()").fetchone()[0]

                    # Get row count
                    try:
                        gold_row_count = conn.execute(f"SELECT COUNT(*) FROM {current_db}.gold.crashes").fetchone()[0]
                    except:
                        gold_row_count = 0

                    # Get latest corr_id and last run timestamp
                    try:
                        result = conn.execute(f"""
                            SELECT corr_id, MAX(inserted_at) as last_run
                            FROM {current_db}.gold.crashes
                            GROUP BY corr_id
                            ORDER BY last_run DESC
                            LIMIT 1
                        """).fetchone()

                        if result:
                            latest_corr_id = result[0]
                            last_run_timestamp = result[1] if result[1] else "N/A"

                    except:
                        pass

                    # Get latest data date fetched (max crash_date from Gold)
                    try:
                        result = conn.execute(f"""
                            SELECT MAX(crash_date) as latest_crash_date
                            FROM {current_db}.gold.crashes
                        """).fetchone()

                        if result and result[0]:
                            latest_data_date = result[0]

                    except:
                        pass
                finally:
                    conn.close()
    except Exception as e:
        st.warning(f"Could not read Gold database: {str(e)}")

    # Get MinIO stats for run count estimate
    run_count = 0
    try:
        from minio import Minio

        minio_client = Minio(
            "minio:9000",
            access_key=os.getenv("MINIO_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_PASS", "minioadmin"),
            secure=False
        )

        # Count unique correlation IDs from raw-data bucket
        if minio_client.bucket_exists("raw-data"):
            objects = minio_client.list_objects("raw-data", prefix="crash/", recursive=True)
            corr_ids = set()
            for obj in objects:
                parts = obj.object_name.split("/")
                if len(parts) >= 2:
                    corr_ids.add(parts[1])  # crash/{corr_id}/...
            run_count = len(corr_ids)
    except:
        pass

    with col1:
        st.metric("Total Runs Completed", f"{run_count}")

    with col2:
        if latest_corr_id != "N/A":
            st.markdown(f"**Latest Corr ID**")
            st.code(latest_corr_id, language=None)
        else:
            st.metric("Latest Corr ID", "N/A")

    with col3:
        st.metric("Gold Row Count", f"{gold_row_count:,}")

    with col4:
        if latest_data_date != "N/A":
            st.metric("Latest Data Date", str(latest_data_date))
        else:
            st.metric("Latest Data Date", "N/A")

    with col5:
        if last_run_timestamp != "N/A":
            st.metric("Last Run Timestamp", str(last_run_timestamp))
        else:
            st.metric("Last Run Timestamp", "N/A")

    st.markdown("---")

    # =============================================================================
    # Latest Run Summary
    # =============================================================================
    st.subheader("🔍 Latest Run Summary")

    if latest_corr_id != "N/A":
        # Try to get detailed run information
        config_type = "Unknown"
        start_time = "N/A"
        end_time = last_run_timestamp
        rows_per_table = {}

        try:
            conn = get_duckdb_connection(gold_db_path, read_only=True)
            if conn is not None:
                try:
                    current_db = conn.execute("SELECT current_database()").fetchone()[0]

                    # Get row count for this specific corr_id
                    result = conn.execute(f"""
                        SELECT COUNT(*) as row_count,
                               MIN(inserted_at) as start_time,
                               MAX(inserted_at) as end_time
                        FROM {current_db}.gold.crashes
                        WHERE corr_id = '{latest_corr_id}'
                    """).fetchone()

                    if result:
                        rows_per_table['crashes'] = result[0]
                        if result[1]:
                            start_time = result[1]
                        if result[2]:
                            end_time = result[2]
                finally:
                    conn.close()
        except:
            pass

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Correlation ID:** `{latest_corr_id}`")
            st.markdown(f"**Config Type:** {config_type}")
            st.markdown("**Status:** ✅ Completed")

        with col2:
            st.markdown("**Start Time:** " + str(start_time))
            st.markdown("**End Time:** " + str(end_time))

        st.markdown("**Rows Processed:**")
        if rows_per_table:
            for table, count in rows_per_table.items():
                st.markdown(f"- {table}: {count:,} rows")
        else:
            st.markdown(f"- Total in Gold: {gold_row_count:,} rows")

        with st.expander("⚠️ Errors / Warnings"):
            st.info("No errors or warnings logged for this run")

        with st.expander("📋 Artifacts"):
            st.markdown(f"**Request JSON:** Check MinIO bucket `raw-data/crash/{latest_corr_id}/` for original API responses")
            st.markdown(f"**Logs:** Container logs available via `docker logs extractor`, `docker logs transformer`, `docker logs cleaner`")
            st.markdown(f"**Sample Outputs:** Check `transform-data/crash/{latest_corr_id}/merged.csv` in MinIO")

    else:
        st.info("No runs detected yet. Use the Data Fetcher tab to trigger a pipeline run.")

    st.markdown("---")

    # =============================================================================
    # Data Quality Metrics
    # =============================================================================
    st.subheader("✅ Data Quality Metrics")

    if os.path.exists(gold_db_path) and gold_row_count > 0:
        try:
            conn = get_duckdb_connection(gold_db_path, read_only=True)
            if conn is not None:
                try:
                    current_db = conn.execute("SELECT current_database()").fetchone()[0]

                    df_sample = conn.execute(f"SELECT * FROM {current_db}.gold.crashes LIMIT 1000").fetchdf()

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        # Missing value rate
                        missing_pct = (df_sample.isnull().sum().sum() / (len(df_sample) * len(df_sample.columns)) * 100)
                        st.metric("Missing Values %", f"{missing_pct:.2f}%")

                    with col2:
                        # Duplicate check
                        duplicate_count = df_sample.duplicated(subset=['crash_record_id']).sum()
                        st.metric("Duplicate Records", f"{duplicate_count}")

                    with col3:
                        # Hit & Run rate
                        if 'hit_and_run_i' in df_sample.columns:
                            hr_rate = (df_sample['hit_and_run_i'].sum() / len(df_sample) * 100)
                            st.metric("Hit & Run Rate", f"{hr_rate:.2f}%")
                finally:
                    conn.close()

        except Exception as e:
            st.error(f"Error calculating quality metrics: {str(e)}")
    else:
        st.info("No data available for quality metrics")

    st.markdown("---")

    # =============================================================================
    # Download Reports
    # =============================================================================
    st.subheader("📥 Download Reports")
    st.markdown("Export pipeline data as CSV files for offline analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Run History")
        st.caption("corrid, mode, window, rows, status, started/ended")

        if os.path.exists(gold_db_path) and gold_row_count > 0:
            try:
                conn = get_duckdb_connection(gold_db_path, read_only=True)
                if conn is not None:
                    try:
                        current_db = conn.execute("SELECT current_database()").fetchone()[0]

                        # Get all correlation IDs with their stats
                        run_history_df = conn.execute(f"""
                            SELECT
                                corr_id,
                                'Unknown' as mode,
                                COUNT(*) as rows,
                                'Completed' as status,
                                MIN(inserted_at) as started,
                                MAX(inserted_at) as ended
                            FROM {current_db}.gold.crashes
                            GROUP BY corr_id
                            ORDER BY MAX(inserted_at) DESC
                        """).fetchdf()

                        csv = run_history_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Run History CSV",
                            data=csv,
                            file_name=f"run_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_run_history"
                        )
                    finally:
                        conn.close()
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("No data available")

    with col2:
        st.markdown("### 📋 Gold Snapshot")
        st.caption("table, row count, latest data date")

        if os.path.exists(gold_db_path) and gold_row_count > 0:
            try:
                conn = get_duckdb_connection(gold_db_path, read_only=True)
                if conn is not None:
                    try:
                        current_db = conn.execute("SELECT current_database()").fetchone()[0]

                        # Get table summary with latest crash_date
                        snapshot_df = conn.execute(f"""
                            SELECT
                                'crashes' as table_name,
                                COUNT(*) as row_count,
                                MAX(crash_date) as latest_data_date
                            FROM {current_db}.gold.crashes
                        """).fetchdf()

                        csv = snapshot_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Gold Snapshot CSV",
                            data=csv,
                            file_name=f"gold_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_gold_snapshot"
                        )
                    finally:
                        conn.close()
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("No data available")

    with col3:
        st.markdown("### ⚠️ Errors Summary")
        st.caption("corrid, type, message counts")

        if os.path.exists(gold_db_path) and gold_row_count > 0:
            try:
                # Create a placeholder errors summary (actual error logging would need backend support)
                errors_data = {
                    'corrid': [latest_corr_id] if latest_corr_id != "N/A" else [],
                    'error_type': ['None'] if latest_corr_id != "N/A" else [],
                    'message': ['No errors logged'] if latest_corr_id != "N/A" else [],
                    'count': [0] if latest_corr_id != "N/A" else []
                }
                errors_df = pd.DataFrame(errors_data)

                csv = errors_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Errors Summary CSV",
                    data=csv,
                    file_name=f"errors_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_errors_summary"
                )
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("No data available")

    st.markdown("---")

    # =============================================================================
    # PDF Report Download
    # =============================================================================
    st.subheader("📄 Comprehensive PDF Report")
    st.markdown("Generate a complete pipeline report with run history, error summary, and project details")

    if os.path.exists(gold_db_path) and gold_row_count > 0:
        if st.button("📥 Generate PDF Report", type="primary", key="generate_pdf"):
            try:
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                from reportlab.lib.enums import TA_CENTER, TA_LEFT
                from io import BytesIO

                # Create PDF buffer
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

                # Container for PDF elements
                elements = []
                styles = getSampleStyleSheet()

                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=24,
                    textColor=colors.HexColor('#1f77b4'),
                    spaceAfter=30,
                    alignment=TA_CENTER
                )

                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=16,
                    textColor=colors.HexColor('#2c3e50'),
                    spaceAfter=12,
                    spaceBefore=12
                )

                # Title
                elements.append(Paragraph("Chicago Crash ETL Pipeline Report", title_style))
                elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))

                # Project Information
                elements.append(Paragraph("Project Information", heading_style))
                project_info = [
                    ['Project Name:', 'Chicago Crash Data ETL Pipeline'],
                    ['Pipeline Type:', 'Medallion Architecture (Bronze → Silver → Gold)'],
                    ['Target Variable:', 'hit_and_run_i (Binary Classification)'],
                    ['Data Source:', 'City of Chicago Open Data Portal'],
                    ['Storage:', 'MinIO (Object Storage) + DuckDB (Analytics Database)'],
                    ['Orchestration:', 'RabbitMQ Message Queue']
                ]
                project_table = Table(project_info, colWidths=[2*inch, 4*inch])
                project_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                elements.append(project_table)
                elements.append(Spacer(1, 0.3*inch))

                # Gold Table Description
                elements.append(Paragraph("Gold Table Schema", heading_style))
                elements.append(Paragraph(
                    f"<b>Table Name:</b> gold.crashes<br/>"
                    f"<b>Total Rows:</b> {gold_row_count:,}<br/>"
                    f"<b>Latest Data Date:</b> {latest_data_date}<br/>"
                    f"<b>Latest Run:</b> {last_run_timestamp}",
                    styles['Normal']
                ))
                elements.append(Spacer(1, 0.2*inch))

                # Key Features Description
                features_desc = """
                <b>Key Features for Hit & Run Prediction:</b><br/>
                • Temporal: crash_hour, crash_day_of_week, is_weekend, hour_bin<br/>
                • Location: latitude, longitude, grid_id, beat_of_occurrence<br/>
                • Environmental: lighting_condition, weather_condition, roadway_surface_cond<br/>
                • Context: posted_speed_limit, traffic_control_device, intersection_related_i<br/>
                • Crash Details: num_units, injuries_total, crash_type, work_zone_i
                """
                elements.append(Paragraph(features_desc, styles['Normal']))
                elements.append(Spacer(1, 0.3*inch))

                # Run History Table
                elements.append(Paragraph("Recent Pipeline Runs", heading_style))

                conn = get_duckdb_connection(gold_db_path, read_only=True)
                if conn is None:
                    st.error("Failed to connect to database for PDF generation")
                    return

                try:
                    current_db = conn.execute("SELECT current_database()").fetchone()[0]

                    run_history_df = conn.execute(f"""
                        SELECT
                            corr_id,
                            'Streaming/Backfill' as mode,
                            COUNT(*) as rows,
                            'Completed' as status,
                            MIN(inserted_at) as started,
                            MAX(inserted_at) as ended
                        FROM {current_db}.gold.crashes
                        GROUP BY corr_id
                        ORDER BY MAX(inserted_at) DESC
                        LIMIT 10
                    """).fetchdf()

                    if not run_history_df.empty:
                        # Prepare table data
                        run_data = [['Correlation ID', 'Rows', 'Status', 'Started', 'Ended']]
                        for _, row in run_history_df.iterrows():
                            run_data.append([
                                str(row['corr_id'])[:30] + '...' if len(str(row['corr_id'])) > 30 else str(row['corr_id']),
                                str(row['rows']),
                                str(row['status']),
                                str(row['started'])[:19] if pd.notna(row['started']) else 'N/A',
                                str(row['ended'])[:19] if pd.notna(row['ended']) else 'N/A'
                            ])

                        run_table = Table(run_data, colWidths=[2*inch, 0.7*inch, 0.9*inch, 1.5*inch, 1.5*inch])
                        run_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ]))
                        elements.append(run_table)
                    else:
                        elements.append(Paragraph("No run history available", styles['Normal']))

                    elements.append(Spacer(1, 0.3*inch))

                    # Error Summary Table
                    elements.append(Paragraph("Error Summary", heading_style))
                    errors_data = [['Correlation ID', 'Error Type', 'Message', 'Count']]
                    if latest_corr_id != "N/A":
                        errors_data.append([latest_corr_id, 'None', 'No errors logged', '0'])
                    else:
                        errors_data.append(['N/A', 'N/A', 'No runs detected', '0'])

                    error_table = Table(errors_data, colWidths=[2.5*inch, 1.5*inch, 2*inch, 0.7*inch])
                    error_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ]))
                    elements.append(error_table)
                    elements.append(Spacer(1, 0.3*inch))

                    # Data Quality Metrics
                    elements.append(Paragraph("Data Quality Metrics", heading_style))

                    df_sample = conn.execute(f"SELECT * FROM {current_db}.gold.crashes LIMIT 1000").fetchdf()
                    missing_pct = (df_sample.isnull().sum().sum() / (len(df_sample) * len(df_sample.columns)) * 100)
                    duplicate_count = df_sample.duplicated(subset=['crash_record_id']).sum()
                    hr_rate = (df_sample['hit_and_run_i'].sum() / len(df_sample) * 100) if 'hit_and_run_i' in df_sample.columns else 0

                    quality_info = [
                        ['Metric', 'Value'],
                        ['Missing Values %', f'{missing_pct:.2f}%'],
                        ['Duplicate Records', f'{duplicate_count}'],
                        ['Hit & Run Rate', f'{hr_rate:.2f}%'],
                        ['Sample Size (for metrics)', f'{len(df_sample):,} rows']
                    ]

                    quality_table = Table(quality_info, colWidths=[3*inch, 3*inch])
                    quality_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]))
                    elements.append(quality_table)
                finally:
                    conn.close()

                # Build PDF
                doc.build(elements)

                # Offer download
                pdf_bytes = buffer.getvalue()
                buffer.close()

                st.download_button(
                    label="💾 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    key="download_pdf_final"
                )

                st.success("✅ PDF report generated successfully!")

            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
    else:
        st.info("No data available to generate report")


def render_model_tab():
    st.header("🤖 ML Model - Hit & Run Prediction")

    # Load model metadata from JSON
    metadata = load_model_metadata(MODEL_METADATA_PATH)

    if metadata is None:
        st.error("❌ Model metadata not loaded. Cannot display model information.")
        st.info("Please ensure the metadata file exists at: `artifacts/model_metadata.json`")
        return

    # =============================================================================
    # Section 1: Model Summary
    # =============================================================================
    st.subheader("📋 Model Summary")

    # Get model info from metadata
    model_type = metadata.get("model_type", "Unknown")
    threshold = metadata.get("threshold", 0.5)
    feature_names = metadata.get("feature_names", [])
    num_features = len(feature_names)

    # Display model info in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Model Type", model_type)
        st.caption("Machine learning algorithm")

    with col2:
        st.metric("Number of Features", num_features)
        st.caption("Input features used for prediction")

    with col3:
        st.metric("Decision Threshold", f"{threshold:.2f}")
        st.caption("Probability cutoff for hit-and-run classification")

    st.markdown("---")

    # Expected Input Description
    st.subheader("📝 Expected Input Features")

    st.markdown(f"""
    The model expects **{num_features} features** from the crash data.

    ⚠️ **IMPORTANT:**
    - Pass **raw column values** exactly as they appear in the database
    - Do **NOT** manually one-hot encode categorical features
    - Do **NOT** manually scale or normalize numeric features
    - The model pipeline handles all preprocessing internally
    """)

    # Display features in a more organized way
    st.markdown("**Feature List:**")

    # Split features into columns for better display
    num_cols = 3
    cols = st.columns(num_cols)

    for idx, feature in enumerate(feature_names):
        col_idx = idx % num_cols
        with cols[col_idx]:
            st.markdown(f"- `{feature}`")

    st.markdown("---")

    st.markdown(f"""
    **Model Output:**
    - **Probability score** (0.0 to 1.0) - likelihood of hit-and-run
    - **Predicted class** (0 or 1) - based on threshold of {threshold:.2f}
        - Probability ≥ {threshold:.2f} → Predicted as **Hit-and-Run** (1)
        - Probability < {threshold:.2f} → Predicted as **Not Hit-and-Run** (0)
    """)

    st.markdown("---")

    # =============================================================================
    # Section 2: Data Selection
    # =============================================================================
    st.subheader("📊 Data Selection")

    # Mode selection
    data_mode = st.radio(
        "Select data source for predictions:",
        options=["Gold Table (DuckDB)", "Test Data Upload (CSV)"],
        horizontal=True,
        help="Choose whether to load data from the Gold database or upload a test CSV file"
    )

    # Initialize session state for storing loaded data
    if 'model_data' not in st.session_state:
        st.session_state.model_data = None

    # =============================================================================
    # Mode 1: Gold Table
    # =============================================================================
    if data_mode == "Gold Table (DuckDB)":
        st.markdown("### Load data from Gold database")

        gold_db_path = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb")

        if not os.path.exists(gold_db_path):
            st.error("❌ Gold database not found. Please run the data pipeline first.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # Date filters
                st.markdown("**Date Range Filter:**")
                start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime("2020-01-01"),
                    help="Filter crashes from this date onwards"
                )
                end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime("2020-01-02"),
                    help="Filter crashes up to this date"
                )

            with col2:
                # Row limit
                st.markdown("**Sample Size:**")
                max_rows = st.number_input(
                    "Maximum number of rows to load",
                    min_value=100,
                    max_value=50000,
                    value=5000,
                    step=500,
                    help="Limit the number of rows to prevent memory issues"
                )

            # Load button
            if st.button("🔍 Load Data from Gold Table", type="primary"):
                with st.spinner("Loading data from Gold database..."):
                    try:
                        conn = get_duckdb_connection(gold_db_path, read_only=True)
                        if conn is None:
                            st.error("Failed to connect to database")
                        else:
                            try:
                                current_db = conn.execute("SELECT current_database()").fetchone()[0]

                                # Build query with date filters and row limit
                                query = f"""
                                    SELECT *
                                    FROM {current_db}.gold.crashes
                                    WHERE crash_date BETWEEN '{start_date}' AND '{end_date}'
                                    LIMIT {max_rows}
                                """

                                # Track database query
                                db_queries_total.inc()
                                df = conn.execute(query).fetchdf()

                                # Track rows loaded
                                if not df.empty:
                                    rows_loaded_total.inc(len(df))

                                if df.empty:
                                    st.warning("⚠️ No data found for the selected date range.")
                                    st.session_state.model_data = None
                                else:
                                    # Verify that the required features exist
                                    missing_features = [f for f in feature_names if f not in df.columns]

                                    if missing_features:
                                        st.error(f"❌ Missing required features in Gold table: {', '.join(missing_features)}")
                                        st.session_state.model_data = None
                                    else:
                                        # Store data in session state
                                        st.session_state.model_data = df
                                        st.success(f"✅ Loaded {len(df):,} rows from Gold table")

                            finally:
                                conn.close()

                    except Exception as e:
                        st.error(f"Error loading data: {str(e)}")
                        st.session_state.model_data = None

    # =============================================================================
    # Mode 2: Test Data Upload
    # =============================================================================
    else:  # Test Data Upload (CSV)
        st.markdown("### Upload test data file")

        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            help="Upload a CSV file containing test data with the same features as training data"
        )

        if uploaded_file is not None:
            # Validate file extension
            file_name = uploaded_file.name
            if not file_name.lower().endswith('.csv'):
                st.error("❌ Invalid file type. Only CSV files (.csv) are allowed.")
                st.session_state.model_data = None
            else:
                try:
                    # Load the CSV file
                    df = pd.read_csv(uploaded_file)

                    # Validate that required features exist
                    missing_features = [f for f in feature_names if f not in df.columns]

                    if missing_features:
                        st.error(f"❌ Missing required features in uploaded file:")
                        st.error(f"Missing columns: {', '.join(missing_features)}")
                        st.info(f"Expected {len(feature_names)} features. Please ensure your CSV contains all required columns.")
                        st.session_state.model_data = None
                    else:
                        # Store data in session state
                        st.session_state.model_data = df
                        st.success(f"✅ File uploaded successfully: {file_name}")
                        st.success(f"✅ Loaded {len(df):,} rows with all required features")

                except Exception as e:
                    st.error(f"❌ Error reading CSV file: {str(e)}")
                    st.session_state.model_data = None
        else:
            st.info("📤 Please upload a CSV file to continue")
            st.session_state.model_data = None

    # =============================================================================
    # Display loaded data preview
    # =============================================================================
    if st.session_state.model_data is not None:
        st.markdown("---")
        st.subheader("📋 Data Preview")

        df = st.session_state.model_data

        # Display metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Rows", f"{len(df):,}")

        with col2:
            st.metric("Total Columns", f"{len(df.columns):,}")

        with col3:
            # Check if target column exists for info
            if 'hit_and_run_i' in df.columns:
                hr_rate = (df['hit_and_run_i'].sum() / len(df) * 100)
                st.metric("Hit & Run Rate", f"{hr_rate:.2f}%")
            else:
                st.metric("Features Available", "✓")

        # Show preview of the data
        st.markdown("**First 10 rows:**")
        st.dataframe(df.head(10), use_container_width=True)

        # Show feature columns that will be used for prediction
        with st.expander("🔍 Feature Columns (for prediction)"):
            available_features = [f for f in feature_names if f in df.columns]
            st.write(f"Available: {len(available_features)} / {len(feature_names)} features")

            # Display in columns
            cols = st.columns(3)
            for idx, feature in enumerate(available_features):
                col_idx = idx % 3
                with cols[col_idx]:
                    st.markdown(f"✓ `{feature}`")

    st.markdown("---")

    # =============================================================================
    # Section 3: Prediction & Metrics
    # =============================================================================
    if st.session_state.model_data is not None:
        st.subheader("🎯 Predictions & Model Performance")

        # Initialize session state for predictions
        if 'predictions' not in st.session_state:
            st.session_state.predictions = None
        if 'probabilities' not in st.session_state:
            st.session_state.probabilities = None

        # Run Predictions Button
        if st.button("🚀 Run Predictions", type="primary", use_container_width=True):
            with st.spinner("Running model predictions..."):
                try:
                    # Load the model
                    model = load_model(MODEL_ARTIFACT_PATH)
                    if model is None:
                        st.error("❌ Failed to load model. Cannot run predictions.")
                    else:
                        # Get the data
                        df = st.session_state.model_data

                        # Extract feature columns
                        X = df[feature_names]

                        # Run predictions and track metrics
                        pred_start = time.time()
                        probabilities = model.predict_proba(X)[:, 1]  # Probability of class 1 (hit-and-run)
                        predictions = (probabilities >= threshold).astype(int)
                        pred_duration = time.time() - pred_start

                        # Track prediction metrics
                        prediction_latency_seconds.observe(pred_duration)
                        predictions_total.inc(len(predictions))

                        # Store in session state
                        st.session_state.probabilities = probabilities
                        st.session_state.predictions = predictions

                        st.success(f"✅ Predictions complete! Scored {len(predictions):,} rows")

                except Exception as e:
                    st.error(f"❌ Error running predictions: {str(e)}")
                    st.session_state.predictions = None
                    st.session_state.probabilities = None

        # Display results if predictions have been run
        if st.session_state.predictions is not None:
            st.markdown("---")

            # Get test metrics from metadata
            test_metrics = metadata.get("test_metrics", {})

            # =================================================================
            # Static Metrics (from training)
            # =================================================================
            st.markdown("### 📊 Static Metrics (Test Set from Training)")
            st.caption("Official metrics from the held-out test set during model training")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                precision_static = test_metrics.get("precision", 0.0)
                st.metric("Precision", f"{precision_static:.1%}")
                st.caption("Of predicted hit-and-runs, what % were correct?")

            with col2:
                recall_static = test_metrics.get("recal", test_metrics.get("recall", 0.0))
                st.metric("Recall", f"{recall_static:.1%}")
                st.caption("Of actual hit-and-runs, what % did we catch?")

            with col3:
                f1_static = test_metrics.get("f1", 0.0)
                st.metric("F1 Score", f"{f1_static:.1%}")
                st.caption("Harmonic mean of precision and recall")

            with col4:
                st.metric("Threshold", f"{threshold:.2f}")
                st.caption("Decision boundary for classification")

            st.markdown("---")

            # =================================================================
            # Live Metrics (computed on loaded data)
            # =================================================================
            st.markdown("### 📈 Live Metrics (Current Data)")
            st.caption("Metrics computed on the data you just loaded")

            df = st.session_state.model_data
            predictions = st.session_state.predictions
            probabilities = st.session_state.probabilities

            # Check if we have ground truth labels
            has_labels = 'hit_and_run_i' in df.columns

            if has_labels:
                # Compute live metrics
                from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

                y_true = df['hit_and_run_i'].values
                y_pred = predictions

                accuracy = accuracy_score(y_true, y_pred)
                precision_live = precision_score(y_true, y_pred, zero_division=0)
                recall_live = recall_score(y_true, y_pred, zero_division=0)
                f1_live = f1_score(y_true, y_pred, zero_division=0)
                cm = confusion_matrix(y_true, y_pred)

                # Display live metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Accuracy", f"{accuracy:.1%}")

                with col2:
                    st.metric("Precision", f"{precision_live:.1%}")

                with col3:
                    st.metric("Recall", f"{recall_live:.1%}")

                with col4:
                    st.metric("F1 Score", f"{f1_live:.1%}")

                # Confusion Matrix
                st.markdown("**Confusion Matrix:**")

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Create confusion matrix display
                    cm_df = pd.DataFrame(
                        cm,
                        index=['Actual: Not H&R (0)', 'Actual: H&R (1)'],
                        columns=['Predicted: Not H&R (0)', 'Predicted: H&R (1)']
                    )
                    st.dataframe(cm_df, use_container_width=True)

                with col2:
                    # Show interpretation
                    tn, fp, fn, tp = cm.ravel()
                    st.markdown(f"""
                    **Breakdown:**
                    - ✅ True Negatives: {tn:,} (Correctly predicted as NOT hit-and-run)
                    - ❌ False Positives: {fp:,} (Incorrectly predicted as hit-and-run)
                    - ❌ False Negatives: {fn:,} (Missed hit-and-runs)
                    - ✅ True Positives: {tp:,} (Correctly caught hit-and-runs)
                    """)

            else:
                # No ground truth - just show prediction distribution
                st.info("ℹ️ No ground truth labels found. Showing prediction distribution only.")

                col1, col2, col3 = st.columns(3)

                with col1:
                    total_predictions = len(predictions)
                    st.metric("Total Predictions", f"{total_predictions:,}")

                with col2:
                    predicted_hr = predictions.sum()
                    st.metric("Predicted Hit & Run", f"{predicted_hr:,}")
                    st.caption(f"{predicted_hr/total_predictions:.1%} of total")

                with col3:
                    predicted_not_hr = total_predictions - predicted_hr
                    st.metric("Predicted NOT Hit & Run", f"{predicted_not_hr:,}")
                    st.caption(f"{predicted_not_hr/total_predictions:.1%} of total")

            st.markdown("---")

            # =================================================================
            # Prediction Distribution
            # =================================================================
            st.markdown("### 📊 Prediction Distribution")

            # Probability distribution histogram
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=probabilities,
                nbinsx=50,
                name='Probability Distribution',
                marker_color='steelblue'
            ))

            # Add threshold line
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Threshold ({threshold:.2f})",
                annotation_position="top right"
            )

            fig.update_layout(
                title="Distribution of Predicted Probabilities",
                xaxis_title="Predicted Probability of Hit-and-Run",
                yaxis_title="Count",
                showlegend=False,
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            # =================================================================
            # Download Predictions
            # =================================================================
            st.markdown("### 💾 Download Results")

            # Add predictions to dataframe
            results_df = df.copy()
            results_df['predicted_probability'] = probabilities
            results_df['predicted_class'] = predictions

            # Convert to CSV
            csv = results_df.to_csv(index=False)

            st.download_button(
                label="📥 Download Predictions as CSV",
                data=csv,
                file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.caption(f"Downloading {len(results_df):,} rows with predictions and probabilities")

    else:
        st.info("👆 Please load data in Section 2 above to run predictions")

    st.markdown("---")


def main():
    # Track page load
    page_loads_total.inc()

    # Load model metadata and update Prometheus metrics
    # Metadata loading is cached, but metrics update on every page load
    metadata = load_model_metadata(MODEL_METADATA_PATH)
    update_model_metrics(metadata)

    # with st.sidebar:
    #     st.title("Navigation")
    #     st.markdown("---")
    #     st.info("**Quick Tips:**\n- Check container health first\n- Use Data Fetcher to load data")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Home",
        "Data Management",
        "Data Fetcher",
        "Scheduler",
        "EDA",
        "Reports",
        "Model"
    ])

    with tab1:
        tab_views_total.labels(tab_name='home').inc()
        render_home_tab()
    with tab2:
        tab_views_total.labels(tab_name='data_management').inc()
        render_data_management_tab()
    with tab3:
        tab_views_total.labels(tab_name='data_fetcher').inc()
        render_data_fetcher_tab()
    with tab4:
        tab_views_total.labels(tab_name='scheduler').inc()
        scheduler_tab()
    with tab5:
        tab_views_total.labels(tab_name='eda').inc()
        render_eda_tab()
    with tab6:
        tab_views_total.labels(tab_name='reports').inc()
        render_reports_tab()
    with tab7:
        tab_views_total.labels(tab_name='model').inc()
        render_model_tab()

if __name__ == "__main__":
    main()
