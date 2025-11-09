import streamlit as st
import json
import subprocess
import os
from datetime import datetime, timedelta
import pika
from crontab import CronTab
import tempfile

def scheduler_tab():
    """
    Streamlit tab for scheduling automated data pipeline runs using cron jobs.
    """
    st.subheader("⏰ Pipeline Scheduler")
    st.markdown("Schedule **automated** pipeline runs using cron jobs")

    # Initialize session state for managing jobs
    if 'scheduled_jobs' not in st.session_state:
        st.session_state.scheduled_jobs = load_existing_jobs()

    # Tabs for different scheduler functions
    tab1, tab2, tab3 = st.tabs(["📅 Create Schedule", "📋 View Jobs", "⚙️ Settings"])

    with tab1:
        create_schedule_ui()
    
    with tab2:
        view_jobs_ui()
    
    with tab3:
        settings_ui()

def create_schedule_ui():
    """UI for creating new scheduled jobs"""
    st.markdown("### 🆕 Create New Scheduled Job")
    
    # Job configuration
    col1, col2 = st.columns([2, 1])
    
    with col1:
        job_name = st.text_input(
            "Job Name",
            placeholder="e.g., Daily Crash Data Sync",
            help="A descriptive name for this scheduled job"
        )
    
    with col2:
        job_enabled = st.checkbox("Enable Job", value=True)

    # Schedule configuration
    st.markdown("#### 📅 Schedule Configuration")
    
    schedule_type = st.selectbox(
        "Schedule Type",
        ["Custom Cron", "Predefined Intervals"],
        help="Choose between custom cron expressions or predefined intervals"
    )
    
    if schedule_type == "Predefined Intervals":
        interval_type = st.selectbox(
            "Interval",
            ["Every Hour", "Every 6 Hours", "Daily", "Weekly", "Monthly"]
        )
        
        if interval_type in ["Daily", "Weekly"]:
            time_col1, time_col2 = st.columns(2)
            with time_col1:
                hour = st.selectbox("Hour", range(24), index=2)
            with time_col2:
                minute = st.selectbox("Minute", range(60), index=0)
        
        if interval_type == "Weekly":
            day_of_week = st.selectbox(
                "Day of Week",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                index=0
            )
        
        # Convert to cron expression
        cron_expression = generate_cron_expression(interval_type, hour if interval_type in ["Daily", "Weekly"] else None, minute if interval_type in ["Daily", "Weekly"] else None, day_of_week if interval_type == "Weekly" else None)
    
    else:  # Custom Cron
        cron_expression = st.text_input(
            "Cron Expression",
            placeholder="0 2 * * *",
            help="Use standard cron format: minute hour day month day_of_week"
        )
    
    # Display cron expression and next run time
    if cron_expression:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Cron Expression:** `{cron_expression}`")
        with col2:
            try:
                next_run = get_next_run_time(cron_expression)
                st.info(f"**Next Run:** {next_run}")
            except:
                st.error("Invalid cron expression")

    st.markdown("---")

    # Data pipeline configuration
    st.markdown("#### 🔧 Pipeline Configuration")
    
    # Auto-generate correlation ID template
    corr_id_template = "scheduled-{job_name}-{timestamp}"
    st.text_input(
        "Correlation ID Template", 
        value=corr_id_template, 
        disabled=True,
        help="Template for generating correlation IDs. {job_name} and {timestamp} will be replaced automatically."
    )

    # Since days configuration
    since_days = st.number_input(
        "Since Days",
        min_value=1,
        max_value=365,
        value=7,
        help="Fetch crashes from the last N days"
    )

    # Data enrichment options
    st.markdown("##### 📊 Data Enrichment")
    
    enrich_col1, enrich_col2 = st.columns(2)
    
    with enrich_col1:
        st.markdown("**🚗 Vehicles Dataset**")
        include_vehicles = st.checkbox("Include Vehicles", value=True, key="sched_vehicles")
        
        if include_vehicles:
            vehicle_columns = st.multiselect(
                "Vehicle columns",
                options=[
                    "crash_record_id", "unit_no", "vehicle_id", "unit_type", "make",
                    "model", "vehicle_year", "travel_direction", "maneuver",
                    "first_contact_point", "vehicle_defect", "vehicle_use", "towed_i"
                ],
                default=["crash_record_id", "unit_no", "vehicle_id", "make", "model", "vehicle_year"],
                key="sched_veh_cols"
            )
    
    with enrich_col2:
        st.markdown("**👥 People Dataset**")
        include_people = st.checkbox("Include People", value=True, key="sched_people")
        
        if include_people:
            people_columns = st.multiselect(
                "People columns",
                options=[
                    "crash_record_id", "person_id", "person_type", "age", "sex",
                    "seat_no", "injury_classification", "safety_equipment",
                    "airbag_deployed", "ejection"
                ],
                default=["crash_record_id", "person_id", "person_type", "age", "sex", "injury_classification"],
                key="sched_ppl_cols"
            )

    # Preview the job configuration
    if job_name and cron_expression:
        job_config = create_job_config(
            job_name, cron_expression, since_days, 
            include_vehicles, vehicle_columns if include_vehicles else [],
            include_people, people_columns if include_people else []
        )
        
        with st.expander("🔍 Preview Job Configuration"):
            st.json(job_config)

    # Create job button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Job", type="primary", disabled=not (job_name and cron_expression)):
            if create_cron_job(job_config, job_enabled):
                st.success(f"✅ Job '{job_name}' created successfully!")
                st.session_state.scheduled_jobs = load_existing_jobs()
                st.rerun()
            else:
                st.error("❌ Failed to create job. Check logs for details.")
    
    with col2:
        if st.button("🧪 Test Run"):
            if job_name and cron_expression:
                if test_job_execution(job_config):
                    st.success("✅ Test run successful!")
                else:
                    st.error("❌ Test run failed!")

def view_jobs_ui():
    """UI for viewing and managing existing jobs"""
    st.markdown("### 📋 Scheduled Jobs")
    
    jobs = st.session_state.scheduled_jobs
    
    if not jobs:
        st.info("📝 No scheduled jobs found. Create one in the 'Create Schedule' tab.")
        return
    
    for i, job in enumerate(jobs):
        with st.expander(f"🔄 {job['name']} - {'✅ Enabled' if job['enabled'] else '❌ Disabled'}"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Schedule:** `{job['cron']}`")
                st.write(f"**Next Run:** {job['next_run']}")

                # Safely access nested config values
                try:
                    since_days = job['config'].get('primary', {}).get('where_by', {}).get('since_days', 'N/A')
                    st.write(f"**Since Days:** {since_days}")
                except:
                    st.write(f"**Since Days:** N/A")

                try:
                    enrich_count = len(job['config'].get('enrich', []))
                    st.write(f"**Enrichment:** {enrich_count} datasets")
                except:
                    st.write(f"**Enrichment:** N/A")
            
            with col2:
                if st.button(f"{'⏸️ Disable' if job['enabled'] else '▶️ Enable'}", key=f"toggle_{i}"):
                    toggle_job(job['name'], not job['enabled'])
                    st.session_state.scheduled_jobs = load_existing_jobs()
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{i}", type="secondary"):
                    if delete_job(job['name']):
                        st.success(f"Job '{job['name']}' deleted!")
                        st.session_state.scheduled_jobs = load_existing_jobs()
                        st.rerun()
                    else:
                        st.error("Failed to delete job")
            
            # Show job configuration
            with st.expander("🔧 Job Configuration"):
                st.json(job['config'])

def settings_ui():
    """UI for scheduler settings"""
    st.markdown("### ⚙️ Scheduler Settings")
    
    # RabbitMQ configuration
    st.markdown("#### 🐰 RabbitMQ Configuration")

    st.info("""
    **Note:** Test connection from Streamlit uses `rabbitmq` (Docker network).
    Cron jobs run on the host and automatically use `localhost:5672`.
    """)

    col1, col2 = st.columns(2)

    with col1:
        rabbitmq_host = st.text_input("RabbitMQ Host (for test)", value="rabbitmq")
        rabbitmq_port = st.number_input("RabbitMQ Port", value=5672)

    with col2:
        rabbitmq_queue = st.text_input("Queue Name", value="extract")
        test_connection = st.button("🔧 Test RabbitMQ Connection")

    if test_connection:
        if test_rabbitmq_connection(rabbitmq_host, rabbitmq_port):
            st.success("✅ RabbitMQ connection successful!")
        else:
            st.error("❌ RabbitMQ connection failed!")
    
    st.markdown("---")
    
    # System information
    st.markdown("#### 📊 System Information")
    
    try:
        # Check if crontab is available
        result = subprocess.run(['which', 'crontab'], capture_output=True, text=True)
        if result.returncode == 0:
            st.success("✅ Crontab is available")
        else:
            st.error("❌ Crontab is not available")
        
        # Show current user's cron jobs
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            st.markdown("**Current Cron Jobs:**")
            st.code(result.stdout if result.stdout.strip() else "No cron jobs found")
        else:
            st.info("No existing cron jobs found")
    
    except Exception as e:
        st.error(f"Error checking system: {str(e)}")

# Helper functions

def generate_cron_expression(interval_type, hour=None, minute=None, day_of_week=None):
    """Generate cron expression from predefined intervals"""
    expressions = {
        "Every Hour": "0 * * * *",
        "Every 6 Hours": "0 */6 * * *",
        "Daily": f"{minute or 0} {hour or 2} * * *",
        "Weekly": f"{minute or 0} {hour or 2} * * {['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].index(day_of_week.lower()) if day_of_week else 0}",
        "Monthly": "0 2 1 * *"
    }
    return expressions.get(interval_type, "0 2 * * *")

def get_next_run_time(cron_expression):
    """Calculate next run time for a cron expression"""
    try:
        from croniter import croniter
        cron = croniter(cron_expression, datetime.now())
        next_run = cron.get_next(datetime)
        return next_run.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Invalid cron expression"

def create_job_config(job_name, cron_expression, since_days, include_vehicles, vehicle_columns, include_people, people_columns):
    """Create job configuration dictionary"""
    config = {
        "name": job_name,
        "cron": cron_expression,
        "config": {
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
    }
    
    # Add enrichment datasets
    if include_vehicles and vehicle_columns:
        config["config"]["enrich"].append({
            "id": "68nd-jvt3",
            "alias": "vehicles",
            "select": ",".join(vehicle_columns)
        })
    
    if include_people and people_columns:
        config["config"]["enrich"].append({
            "id": "u6pd-qa9d",
            "alias": "people",
            "select": ",".join(people_columns)
        })
    
    return config

def create_cron_job(job_config, enabled=True):
    """Create a new cron job"""
    try:
        # Use the standalone pipeline_scheduler.py script
        scheduler_script = "/home/fletcher.newman/Pipeline/streamlit_frontend/pipeline_scheduler.py"

        # Save job config to a JSON file
        config_dir = "/tmp/pipeline_configs"
        os.makedirs(config_dir, exist_ok=True)

        safe_name = job_config['name'].replace(' ', '_').replace('/', '_').lower()
        config_file = f"{config_dir}/{safe_name}.json"

        with open(config_file, 'w') as f:
            json.dump(job_config['config'], f, indent=2)

        # Create the script that will be executed by cron
        # Note: Cron jobs run on the host, so use localhost instead of rabbitmq hostname
        script_content = f'''#!/bin/bash
# Auto-generated cron job for: {job_config["name"]}
# Generated on: {datetime.now().isoformat()}

# Execute pipeline scheduler
python3 {scheduler_script} \\
    --job-name "{job_config['name']}" \\
    --config-file "{config_file}" \\
    --rabbitmq-host localhost \\
    --rabbitmq-port 5672 \\
    --queue extract \\
    >> /tmp/pipeline_scheduler.log 2>&1
'''
        
        # Save script to temporary file
        script_path = f"/tmp/pipeline_job_{job_config['name'].replace(' ', '_').lower()}.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        # Add to crontab
        cron_command = f"{job_config['cron']} {script_path}"
        if not enabled:
            cron_command = f"# {cron_command}"
        
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Add new job
        new_crontab = current_crontab + f"\n# Job: {job_config['name']}\n{cron_command}\n"
        
        # Write back to crontab
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(new_crontab)
            temp_file = f.name
        
        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        os.unlink(temp_file)
        
        return result.returncode == 0
        
    except Exception as e:
        st.error(f"Error creating cron job: {str(e)}")
        return False

def load_existing_jobs():
    """Load existing cron jobs from crontab"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            return []

        jobs = []
        lines = result.stdout.split('\n')
        current_job = None

        for line in lines:
            line = line.strip()
            if line.startswith('# Job:'):
                current_job = line.replace('# Job:', '').strip()
            elif current_job and line and not line.startswith('# Job:'):
                is_enabled = not line.startswith('#')

                # Remove leading # if disabled
                cron_line = line.lstrip('#').strip()

                # Parse cron line
                parts = cron_line.split(' ', 5)
                if len(parts) >= 6:
                    cron_expr = ' '.join(parts[:5])
                    script_path = parts[5]

                    # Load job config from saved JSON file
                    safe_name = current_job.replace(' ', '_').replace('/', '_').lower()
                    config_file = f"/tmp/pipeline_configs/{safe_name}.json"

                    job_config = {"note": "Config file not found"}
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r') as f:
                                job_config = json.load(f)
                        except:
                            job_config = {"note": "Failed to parse config file"}

                    jobs.append({
                        'name': current_job,
                        'cron': cron_expr,
                        'enabled': is_enabled,
                        'next_run': get_next_run_time(cron_expr) if is_enabled else 'Disabled',
                        'config': job_config
                    })

                current_job = None

        return jobs

    except Exception as e:
        st.error(f"Error loading jobs: {str(e)}")
        return []

def toggle_job(job_name, enabled):
    """Enable or disable a cron job"""
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            return False

        lines = result.stdout.split('\n')
        new_lines = []
        found = False

        for i, line in enumerate(lines):
            # Look for the job marker
            if line.strip() == f"# Job: {job_name}":
                found = True
                new_lines.append(line)

                # Process the next line (the actual cron command)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]

                    if enabled:
                        # Remove comment if present
                        if next_line.strip().startswith('#') and not next_line.strip().startswith('# Job:'):
                            next_line = next_line.lstrip('#').lstrip()
                    else:
                        # Add comment if not present
                        if not next_line.strip().startswith('#'):
                            next_line = f"# {next_line}"

                    lines[i + 1] = next_line
            else:
                new_lines.append(line)

        if not found:
            return False

        # Write back to crontab
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('\n'.join(lines))
            temp_file = f.name

        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        os.unlink(temp_file)

        return result.returncode == 0

    except Exception as e:
        st.error(f"Error toggling job: {str(e)}")
        return False

def delete_job(job_name):
    """Delete a cron job from crontab"""
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            return False

        lines = result.stdout.split('\n')
        new_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            # Look for the job marker
            if line.strip() == f"# Job: {job_name}":
                skip_next = True
                continue  # Skip the marker line

            # Skip the cron command line after the marker
            if skip_next:
                skip_next = False

                # Also delete the associated script file if it exists
                if line.strip() and not line.strip().startswith('#'):
                    # Extract script path from cron line
                    parts = line.split()
                    if len(parts) >= 6:
                        script_path = parts[5]
                        if os.path.exists(script_path):
                            try:
                                os.unlink(script_path)
                            except:
                                pass

                # Also delete config file
                safe_name = job_name.replace(' ', '_').replace('/', '_').lower()
                config_file = f"/tmp/pipeline_configs/{safe_name}.json"
                if os.path.exists(config_file):
                    try:
                        os.unlink(config_file)
                    except:
                        pass

                continue  # Skip the cron command line

            new_lines.append(line)

        # Write back to crontab
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('\n'.join(new_lines))
            temp_file = f.name

        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        os.unlink(temp_file)

        return result.returncode == 0

    except Exception as e:
        st.error(f"Error deleting job: {str(e)}")
        return False

def test_job_execution(job_config):
    """Test job execution by sending message to RabbitMQ"""
    try:
        # Generate test correlation ID
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        test_config = job_config['config'].copy()
        test_config['corr_id'] = f"test-{job_config['name'].replace(' ', '-').lower()}-{timestamp}"
        
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
        channel = connection.channel()
        channel.queue_declare(queue='extract', durable=True)
        
        # Publish test message
        channel.basic_publish(
            exchange='',
            routing_key='extract',
            body=json.dumps(test_config),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        connection.close()
        return True
        
    except Exception as e:
        st.error(f"Test execution failed: {str(e)}")
        return False

def test_rabbitmq_connection(host, port):
    """Test RabbitMQ connection"""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
        connection.close()
        return True
    except:
        return False

# Example usage in main Streamlit app:
if __name__ == "__main__":
    scheduler_tab()