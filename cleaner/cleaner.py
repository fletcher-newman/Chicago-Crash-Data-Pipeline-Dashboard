# cleaner/cleaner.py
import os
import json
import logging
import time
import random
import socket
import traceback
from threading import Thread

import pika
from pika.exceptions import AMQPConnectionError, ProbableAccessDeniedError, ProbableAuthenticationError

# Prometheus metrics
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from cleaning_rules import clean_data
from duckdb_writer import write_to_gold

# ---------------------------------
# Logging
# ---------------------------------
logging.basicConfig(level=logging.INFO, format="[cleaner] %(message)s")
logging.getLogger("pika").setLevel(logging.WARNING)

# ---------------------------------
# Prometheus Metrics
# ---------------------------------
# Service uptime
cleaner_uptime = Gauge(
    'cleaner_uptime_seconds',
    'Time in seconds since the cleaner service started'
)

# Job counters
jobs_processed_total = Counter(
    'cleaner_jobs_processed_total',
    'Total number of cleaning jobs processed'
)

jobs_success_total = Counter(
    'cleaner_jobs_success_total',
    'Total number of successful cleaning jobs'
)

jobs_failed_total = Counter(
    'cleaner_jobs_failed_total',
    'Total number of failed cleaning jobs'
)

# Rows processed
rows_read_total = Counter(
    'cleaner_rows_read_total',
    'Total number of rows read from transformed data'
)

rows_written_total = Counter(
    'cleaner_rows_written_total',
    'Total number of rows written to Gold database'
)

# Job duration
job_duration_seconds = Histogram(
    'cleaner_job_duration_seconds',
    'Time spent processing a complete cleaning job',
    buckets=[0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120]
)

# Cleaning operation duration
cleaning_duration_seconds = Histogram(
    'cleaner_cleaning_duration_seconds',
    'Time spent cleaning data',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

# DuckDB write duration
duckdb_write_duration_seconds = Histogram(
    'cleaner_duckdb_write_duration_seconds',
    'Time spent writing data to DuckDB',
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)

# Current state
current_jobs_in_progress = Gauge(
    'cleaner_jobs_in_progress',
    'Number of cleaning jobs currently being processed'
)

# Last success timestamp (Unix time)
last_success_timestamp = Gauge(
    'cleaner_last_success_timestamp_seconds',
    'Unix timestamp of the last successful cleaning job'
)

# ---------------------------------
# Configuration from Environment
# ---------------------------------
RABBIT_URL = os.getenv("RABBITMQ_URL")
CLEAN_QUEUE = os.getenv("CLEAN_QUEUE", "clean")
GOLD_DB_PATH = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb")

# Validate required config
if not RABBIT_URL:
    raise ValueError("RABBITMQ_URL environment variable is required")

logging.info(f"Configuration loaded:")
logging.info(f"  RABBIT_URL: {RABBIT_URL}")
logging.info(f"  CLEAN_QUEUE: {CLEAN_QUEUE}")
logging.info(f"  GOLD_DB_PATH: {GOLD_DB_PATH}")


# ---------------------------------
# Helper: Wait for RabbitMQ
# ---------------------------------
def wait_for_port(host: str, port: int, tries: int = 60, delay: float = 1.0) -> bool:
    """
    Wait for a TCP port to become available.

    Args:
        host: Hostname to connect to
        port: Port number
        tries: Number of attempts
        delay: Delay between attempts in seconds

    Returns:
        True if port is available, False otherwise
    """
    for i in range(tries):
        try:
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except OSError:
            if i % 10 == 0 and i > 0:
                logging.info(f"Still waiting for {host}:{port} (attempt {i}/{tries})")
            time.sleep(delay)
    return False


# ---------------------------------
# Message Handler
# ---------------------------------
def process_clean_job(msg: dict) -> None:
    """
    Process a single clean job message.

    Args:
        msg: Message dict from RabbitMQ with structure:
             {
                 "type": "clean",
                 "corr_id": "2025-10-07-18-15-58",
                 "xform_bucket": "transform-data",
                 "prefix": "crash",
                 "gold_db_path": "/data/gold/gold.duckdb",  # optional
                 "gold_table": "crashes"                     # optional (table name within gold schema)
             }

    Raises:
        Exception: If cleaning or writing fails
    """
    # Extract required fields
    corr_id = msg.get("corr_id")
    if not corr_id:
        raise ValueError("Missing required field: corr_id")

    # Use message-specific db_path or fall back to env var
    db_path = msg.get("gold_db_path", GOLD_DB_PATH)

    logging.info(f"========================================")
    logging.info(f"Processing clean job: corr_id={corr_id}")
    logging.info(f"Target DB: {db_path}")
    logging.info(f"========================================")

    # Step 1: Clean the data
    clean_start = time.time()
    cleaned_df = clean_data(corr_id)
    cleaning_duration_seconds.observe(time.time() - clean_start)

    # Track rows read
    rows_read_total.inc(len(cleaned_df))

    # Step 2: Write to Gold
    write_start = time.time()
    stats = write_to_gold(cleaned_df, corr_id, db_path)
    duckdb_write_duration_seconds.observe(time.time() - write_start)

    # Track rows written
    if 'inserted' in stats:
        rows_written_total.inc(stats['inserted'])

    # Step 3: Log results
    # logging.info(f"========================================")
    # logging.info(f"Job complete for corr_id={corr_id}")
    # logging.info(f"  Rows before: {stats['before_count']}")
    # logging.info(f"  Rows after: {stats['after_count']}")
    # logging.info(f"  Inserted: {stats['inserted']}")
    # logging.info(f"  Skipped: {stats['skipped']} (duplicates)")
    # logging.info(f"  Integrity: {'PASSED' if stats['integrity_passed'] else 'FAILED'}")
    # logging.info(f"========================================")

    # if not stats['integrity_passed']:
    #     logging.warning("Integrity checks failed - review duckdb_writer logs")


# ---------------------------------
# RabbitMQ Consumer
# ---------------------------------
def start_consumer():
    """
    Start the RabbitMQ consumer that listens for clean jobs.

    This function runs indefinitely, processing messages from the clean queue.
    """
    logging.info("Starting Cleaner consumer...")

    # Parse RabbitMQ URL to get connection parameters
    params = pika.URLParameters(RABBIT_URL)
    host = params.host or "rabbitmq"
    port = params.port or 5672

    # Wait for RabbitMQ to be available
    logging.info(f"Waiting for RabbitMQ at {host}:{port}...")
    if not wait_for_port(host, port, tries=60, delay=1.0):
        raise SystemExit(f"RabbitMQ not reachable at {host}:{port} after waiting")

    # Connect to RabbitMQ with retries
    max_tries = 60
    base_delay = 1.5
    conn = None

    for i in range(1, max_tries + 1):
        try:
            conn = pika.BlockingConnection(params)
            logging.info("Connected to RabbitMQ")
            break
        except (AMQPConnectionError, ProbableAccessDeniedError, ProbableAuthenticationError) as e:
            if i == 1:
                logging.info(f"Waiting for RabbitMQ authentication @ {RABBIT_URL}...")
            if i % 10 == 0:
                logging.info(f"Still waiting (attempt {i}/{max_tries}): {e.__class__.__name__}")
            time.sleep(base_delay + random.random())

    if conn is None or not conn.is_open:
        raise SystemExit("Could not connect to RabbitMQ after multiple attempts")

    # Set up channel and queue
    ch = conn.channel()
    ch.queue_declare(queue=CLEAN_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)  # Process one message at a time

    # Message callback
    def on_message(channel, method, properties, body):
        """
        Callback when a message is received from RabbitMQ.

        Args:
            channel: Pika channel
            method: Delivery method
            properties: Message properties
            body: Message body (bytes)
        """
        start = time.time()

        # Track job in progress
        current_jobs_in_progress.inc()
        jobs_processed_total.inc()

        try:
            # Parse message
            msg = json.loads(body.decode("utf-8"))
            msg_type = msg.get("type", "")

            # Validate message type
            if msg_type != "clean":
                logging.warning(f"Ignoring message with type={msg_type!r}")
                jobs_failed_total.inc()
                current_jobs_in_progress.dec()
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Process the clean job
            process_clean_job(msg)

            # Track success
            jobs_success_total.inc()

            # --- ADD THIS LINE ---
            # Set the gauge to the current Unix timestamp
            last_success_timestamp.set_to_current_time() 
            # ---------------------

            # ACK the message (success)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logging.info("Message acknowledged (ACK)")

        except Exception as e:
            # Log the error
            logging.error(f"Error processing message: {e}")
            logging.error(traceback.format_exc())

            # Track failure
            jobs_failed_total.inc()

            # NACK the message (failure, don't requeue to avoid loops)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logging.error("Message not acknowledged (NACK, no requeue)")

        finally:
            # Record job duration and decrement in-progress counter
            duration = time.time() - start
            job_duration_seconds.observe(duration)
            current_jobs_in_progress.dec()

    # Start consuming
    logging.info(f"Listening for messages on queue '{CLEAN_QUEUE}'...")
    logging.info("Press Ctrl+C to stop")
    ch.basic_consume(queue=CLEAN_QUEUE, on_message_callback=on_message)

    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
        try:
            ch.stop_consuming()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        logging.info("Cleaner stopped")


# ---------------------------------
# Main Entry Point
# ---------------------------------
if __name__ == "__main__":
    # Start Prometheus metrics HTTP server
    start_http_server(8000)
    logging.info("Metrics server listening on :8000")

    # Start uptime tracking thread
    start_time = time.time()
    def update_uptime():
        while True:
            cleaner_uptime.set(time.time() - start_time)
            time.sleep(10)

    uptime_thread = Thread(target=update_uptime, daemon=True)
    uptime_thread.start()

    try:
        start_consumer()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.error(traceback.format_exc())
        raise SystemExit(1)
