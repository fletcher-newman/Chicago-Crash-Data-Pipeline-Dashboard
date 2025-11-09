#!/usr/bin/env python3
"""
Manually trigger a clean job by publishing a message to RabbitMQ clean queue.
Useful for testing without re-running extractor/transformer.
"""
import pika
import json
import sys

# Configuration
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
CLEAN_QUEUE = "clean"

def publish_clean_job(corr_id: str):
    """
    Publish a clean job message to RabbitMQ.

    Args:
        corr_id: The correlation ID to clean (e.g., "2025-10-14-00-26-56")
    """
    # Build the message
    message = {
        "type": "clean",
        "corr_id": corr_id,
        "xform_bucket": "transform-data",
        "prefix": "crash",
        "gold_db_path": "/data/gold/gold.duckdb",
        "gold_table": "gold.crashes"
    }

    # Connect to RabbitMQ
    print(f"Connecting to RabbitMQ at {RABBITMQ_URL}...")
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Declare queue (in case it doesn't exist)
    channel.queue_declare(queue=CLEAN_QUEUE, durable=True)

    # Publish message
    channel.basic_publish(
        exchange='',
        routing_key=CLEAN_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )

    print(f"✓ Published clean job to '{CLEAN_QUEUE}' queue")
    print(f"  corr_id: {corr_id}")
    print(f"  Message: {json.dumps(message, indent=2)}")

    # Close connection
    connection.close()
    print("\nNow check the cleaner logs:")
    print("  docker logs -f cleaner")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_trigger_clean.py <corr_id>")
        print("Example: python test_trigger_clean.py 2025-10-14-00-26-56")
        print("\nAvailable corr_ids (check MinIO transform-data bucket):")
        sys.exit(1)

    corr_id = sys.argv[1]
    publish_clean_job(corr_id)
