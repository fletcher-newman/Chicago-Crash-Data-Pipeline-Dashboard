#!/usr/bin/env python3
"""
Pipeline Scheduler Script
Standalone script for triggering data pipeline jobs via RabbitMQ.
This script is executed by cron jobs created through the Streamlit scheduler interface.
"""

import json
import sys
import os
import argparse
from datetime import datetime
import pika
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/pipeline_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_job_config(config_file):
    """Load job configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load job config from {config_file}: {e}")
        return None

def generate_correlation_id(job_name):
    """Generate a unique correlation ID for the job"""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    safe_job_name = job_name.replace(' ', '-').replace('_', '-').lower()
    return f"scheduled-{safe_job_name}-{timestamp}"

def publish_to_rabbitmq(config, rabbitmq_host='rabbitmq', rabbitmq_port=5672, queue_name='extract'):
    """Publish job configuration to RabbitMQ"""
    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port)
        )
        channel = connection.channel()
        
        # Declare queue (ensure it exists)
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(config),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        
        connection.close()
        logger.info(f"Successfully published job to RabbitMQ queue '{queue_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish to RabbitMQ: {e}")
        return False

def execute_pipeline_job(job_name, config_data=None, config_file=None):
    """Execute a scheduled pipeline job"""
    logger.info(f"Starting scheduled job: {job_name}")
    
    # Load configuration
    if config_data:
        config = config_data
    elif config_file:
        config = load_job_config(config_file)
        if not config:
            return False
    else:
        logger.error("No configuration provided")
        return False
    
    # Generate correlation ID
    if 'corr_id' not in config:
        config['corr_id'] = generate_correlation_id(job_name)
    
    # Log job details
    logger.info(f"Job: {job_name}")
    logger.info(f"Correlation ID: {config['corr_id']}")
    logger.info(f"Mode: {config.get('mode', 'unknown')}")
    logger.info(f"Source: {config.get('source', 'unknown')}")
    
    # Publish to RabbitMQ
    success = publish_to_rabbitmq(config)
    
    if success:
        logger.info(f"Job '{job_name}' completed successfully")
    else:
        logger.error(f"Job '{job_name}' failed")
    
    return success

def create_default_config(since_days=7, include_vehicles=True, include_people=True):
    """Create a default streaming configuration"""
    config = {
        "mode": "streaming",
        "source": "crash",
        "join_key": "crash_record_id",
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
    
    # Add vehicles enrichment
    if include_vehicles:
        config["enrich"].append({
            "id": "68nd-jvt3",
            "alias": "vehicles",
            "select": "crash_record_id,unit_no,vehicle_id,unit_type,make,model,vehicle_year,travel_direction,maneuver,first_contact_point,vehicle_defect,vehicle_use,towed_i"
        })
    
    # Add people enrichment
    if include_people:
        config["enrich"].append({
            "id": "u6pd-qa9d",
            "alias": "people",
            "select": "crash_record_id,person_id,person_type,age,sex,seat_no,injury_classification,safety_equipment,airbag_deployed,ejection"
        })
    
    return config

def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='Execute scheduled pipeline jobs')
    parser.add_argument('--job-name', required=True, help='Name of the job')
    parser.add_argument('--config-file', help='Path to job configuration JSON file')
    parser.add_argument('--since-days', type=int, default=7, help='Number of days to fetch data for')
    parser.add_argument('--rabbitmq-host', default='rabbitmq', help='RabbitMQ host')
    parser.add_argument('--rabbitmq-port', type=int, default=5672, help='RabbitMQ port')
    parser.add_argument('--queue', default='extract', help='RabbitMQ queue name')
    parser.add_argument('--include-vehicles', action='store_true', default=True, help='Include vehicles data')
    parser.add_argument('--include-people', action='store_true', default=True, help='Include people data')
    parser.add_argument('--test', action='store_true', help='Test mode - print config without publishing')
    
    args = parser.parse_args()
    
    # Load or create configuration
    if args.config_file and os.path.exists(args.config_file):
        config = load_job_config(args.config_file)
        if not config:
            sys.exit(1)
    else:
        config = create_default_config(
            since_days=args.since_days,
            include_vehicles=args.include_vehicles,
            include_people=args.include_people
        )
    
    # Test mode - just print the configuration
    if args.test:
        print("Test mode - Job configuration:")
        print(json.dumps(config, indent=2))
        return
    
    # Execute the job
    success = execute_pipeline_job(args.job_name, config_data=config)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

# Example usage:
# python3 pipeline_scheduler.py --job-name "Daily Crash Sync" --since-days 1
# python3 pipeline_scheduler.py --job-name "Weekly Full Sync" --config-file /path/to/config.json
# python3 pipeline_scheduler.py --job-name "Test Job" --test