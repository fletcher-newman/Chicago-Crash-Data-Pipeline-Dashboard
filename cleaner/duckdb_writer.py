# cleaner/duckdb_writer.py
import duckdb
import pandas as pd
import logging
import os
from datetime import datetime
from typing import Dict

# ---------------------------------
# Logging
# ---------------------------------
logging.basicConfig(level=logging.INFO, format="[cleaner.duckdb_writer] %(message)s")


def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """
    Create or connect to a DuckDB database.

    Args:
        db_path: Path to the DuckDB file (e.g., /data/gold/gold.duckdb)

    Returns:
        DuckDB connection object
    """
    # Create parent directory if it doesn't exist
    parent_dir = os.path.dirname(db_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
        logging.info(f"Created directory: {parent_dir}")

    # Connect to DuckDB (creates file if it doesn't exist)
    conn = duckdb.connect(db_path)
    logging.info(f"Connected to DuckDB at: {db_path}")

    return conn


def ensure_schema_exists(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Create the gold schema and crashes table if they don't exist.

    Args:
        conn: DuckDB connection
    """
    logging.info("Ensuring gold schema and table exist")

    # First, check what database/catalog we're using
    current_db = conn.execute("SELECT current_database()").fetchone()[0]
    logging.info(f"Current database/catalog: {current_db}")

    # Create schema in the current database
    conn.execute("CREATE SCHEMA IF NOT EXISTS gold;")

    # Create table with all cleaned columns
    # Based on your cleaning_rules.py output
    # Use the current database catalog explicitly
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {current_db}.gold.crashes (
            -- Primary Key
            crash_record_id VARCHAR PRIMARY KEY,

            -- Temporal features
            crash_date DATE,
            crash_day_of_week INTEGER,
            crash_hour INTEGER,
            is_weekend INTEGER,
            hour_bin VARCHAR,

            -- Location features
            beat_of_occurrence INTEGER,
            latitude DOUBLE,
            longitude DOUBLE,
            lat_bin DOUBLE,
            lng_bin DOUBLE,
            grid_id VARCHAR,

            -- Crash characteristics
            crash_type VARCHAR,
            num_units INTEGER,
            injuries_total DOUBLE,

            -- Road and environment
            lighting_condition VARCHAR,
            posted_speed_limit INTEGER,
            road_defect VARCHAR,
            roadway_surface_cond VARCHAR,
            street_direction VARCHAR,
            trafficway_type VARCHAR,
            weather_condition VARCHAR,
            traffic_control_device VARCHAR,

            -- Boolean flags (stored as integers: 0 or 1)
            hit_and_run_i INTEGER,
            intersection_related_i INTEGER,
            work_zone_i INTEGER,
            private_property_i INTEGER,

            -- Metadata (tracking which run inserted/updated this row)
            corr_id VARCHAR,
            inserted_at TIMESTAMP,
            updated_at TIMESTAMP
        );
    """)

    logging.info("Schema and table ready")


def upsert_data(df: pd.DataFrame, conn: duckdb.DuckDBPyConnection, corr_id: str) -> Dict[str, int]:
    """
    Insert cleaned data into gold.crashes table with upsert logic.

    Args:
        df: Cleaned DataFrame from cleaning_rules.py
        conn: DuckDB connection
        corr_id: Correlation ID for this data run

    Returns:
        Dict with stats: before_count, after_count, inserted, skipped
    """
    logging.info(f"Starting upsert for corr_id={corr_id}")

    # Get current database/catalog name
    current_db = conn.execute("SELECT current_database()").fetchone()[0]

    # Get row count before insert
    before_count = conn.execute(f"SELECT COUNT(*) FROM {current_db}.gold.crashes").fetchone()[0]
    logging.info(f"Rows in {current_db}.gold.crashes before insert: {before_count}")

    # Add metadata columns to DataFrame
    df = df.copy()
    df['corr_id'] = corr_id
    df['inserted_at'] = datetime.now()
    df['updated_at'] = datetime.now()

    # Register DataFrame as a temporary view in DuckDB
    conn.register('temp_cleaned', df)

    # Insert with ON CONFLICT DO NOTHING (skip duplicates based on PRIMARY KEY)
    # IMPORTANT: Explicitly specify column order to match table schema
    logging.info(f"Inserting {len(df)} rows from DataFrame")
    conn.execute(f"""
        INSERT INTO {current_db}.gold.crashes (
            crash_record_id,
            crash_date,
            crash_day_of_week,
            crash_hour,
            is_weekend,
            hour_bin,
            beat_of_occurrence,
            latitude,
            longitude,
            lat_bin,
            lng_bin,
            grid_id,
            crash_type,
            num_units,
            injuries_total,
            lighting_condition,
            posted_speed_limit,
            road_defect,
            roadway_surface_cond,
            street_direction,
            trafficway_type,
            weather_condition,
            traffic_control_device,
            hit_and_run_i,
            intersection_related_i,
            work_zone_i,
            private_property_i,
            corr_id,
            inserted_at,
            updated_at
        )
        SELECT
            crash_record_id,
            crash_date,
            crash_day_of_week,
            crash_hour,
            is_weekend,
            hour_bin,
            beat_of_occurrence,
            latitude,
            longitude,
            lat_bin,
            lng_bin,
            grid_id,
            crash_type,
            num_units,
            injuries_total,
            lighting_condition,
            posted_speed_limit,
            road_defect,
            roadway_surface_cond,
            street_direction,
            trafficway_type,
            weather_condition,
            traffic_control_device,
            hit_and_run_i,
            intersection_related_i,
            work_zone_i,
            private_property_i,
            corr_id,
            inserted_at,
            updated_at
        FROM temp_cleaned
        ON CONFLICT (crash_record_id) DO NOTHING
    """)

    # Get row count after insert
    after_count = conn.execute(f"SELECT COUNT(*) FROM {current_db}.gold.crashes").fetchone()[0]

    # Calculate stats
    inserted = after_count - before_count
    skipped = len(df) - inserted

    stats = {
        "before_count": before_count,
        "after_count": after_count,
        "inserted": inserted,
        "skipped": skipped
    }

    logging.info(f"Upsert complete: {inserted} inserted, {skipped} skipped (duplicates)")

    return stats


def verify_integrity(conn: duckdb.DuckDBPyConnection) -> bool:
    """
    Verify data integrity in gold.crashes table.

    Args:
        conn: DuckDB connection

    Returns:
        True if all checks pass, False otherwise
    """
    logging.info("Verifying data integrity")

    # Get current database/catalog name
    current_db = conn.execute("SELECT current_database()").fetchone()[0]

    all_checks_passed = True

    # Check 1: No duplicate crash_record_ids
    dupes = conn.execute(f"""
        SELECT crash_record_id, COUNT(*) as count
        FROM {current_db}.gold.crashes
        GROUP BY crash_record_id
        HAVING COUNT(*) > 1
    """).fetchall()

    if dupes:
        logging.error(f"Found {len(dupes)} duplicate crash_record_ids!")
        for crash_id, count in dupes[:5]:  # Show first 5
            logging.error(f"  {crash_id}: {count} occurrences")
        all_checks_passed = False
    else:
        logging.info("✓ No duplicate crash_record_ids")

    # Check 2: No nulls in primary key
    null_ids = conn.execute(f"""
        SELECT COUNT(*) FROM {current_db}.gold.crashes WHERE crash_record_id IS NULL
    """).fetchone()[0]

    if null_ids > 0:
        logging.error(f"Found {null_ids} NULL crash_record_ids!")
        all_checks_passed = False
    else:
        logging.info("✓ No NULL primary keys")

    # Check 3: Show total row count
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {current_db}.gold.crashes").fetchone()[0]
    logging.info(f"✓ Total rows in {current_db}.gold.crashes: {total_rows}")

    # Check 4: Show sample of recent data
    # sample = conn.execute("""
    #     SELECT crash_record_id, corr_id, inserted_at
    #     FROM gold.crashes
    #     ORDER BY inserted_at DESC
    #     LIMIT 5
    # """).fetchall()

    # logging.info("Sample of most recent insertions:")
    # for row in sample:
    #     logging.info(f"  {row}")

    return all_checks_passed


def write_to_gold(df: pd.DataFrame, corr_id: str, db_path: str) -> Dict[str, int]:
    """
    Main function: Write cleaned DataFrame to Gold layer in DuckDB.

    This is the function that cleaner.py will call.

    Args:
        df: Cleaned DataFrame from cleaning_rules.clean_data()
        corr_id: Correlation ID for this data run
        db_path: Path to DuckDB file (e.g., /data/gold/gold.duckdb)

    Returns:
        Dict with insert statistics
    """
    logging.info(f"=== Writing to Gold layer ===")
    logging.info(f"corr_id: {corr_id}")
    logging.info(f"db_path: {db_path}")
    logging.info(f"DataFrame: {len(df)} rows, {len(df.columns)} columns")

    # Connect to DuckDB
    conn = get_connection(db_path)

    try:
        # Ensure schema exists
        ensure_schema_exists(conn)

        # Upsert data
        stats = upsert_data(df, conn, corr_id)

        # Verify integrity
        integrity_ok = verify_integrity(conn)

        if not integrity_ok:
            logging.warning("Integrity checks failed - review logs above")

        stats['integrity_passed'] = integrity_ok

        logging.info(f"=== Gold write complete ===")
        return stats

    finally:
        # Always close connection
        conn.close()
        logging.info("DuckDB connection closed")


if __name__ == "__main__":
    # Test the writer with sample data
    import sys

    if len(sys.argv) < 2:
        print("Usage: python duckdb_writer.py <corr_id>")
        print("Example: python duckdb_writer.py 2025-10-07-18-15-58")
        sys.exit(1)

    test_corr_id = sys.argv[1]

    # Import cleaning function
    from cleaning_rules import clean_data

    # Clean the data
    print(f"Cleaning data for corr_id={test_corr_id}...")
    cleaned_df = clean_data(test_corr_id)

    # Write to Gold
    db_path = os.getenv("GOLD_DB_PATH", "/data/gold/gold.duckdb") # "./TEST_gold.duckdb"
    print(f"\nWriting to Gold at {db_path}...")
    stats = write_to_gold(cleaned_df, test_corr_id, db_path)

    print(f"\n=== Results ===")
    print(f"Before: {stats['before_count']} rows")
    print(f"After: {stats['after_count']} rows")
    print(f"Inserted: {stats['inserted']} rows")
    print(f"Skipped: {stats['skipped']} rows (duplicates)")
    print(f"Integrity: {'PASSED' if stats['integrity_passed'] else 'FAILED'}")

# TEST RUN 
# Open RabbitMQ Management UI: http://localhost:15672
# Login with guest/guest
# Go to Queues tab
# Click on the clean queue
# Expand "Publish message"
# In the Payload field, enter:
# {
#   "type": "clean",
#   "corr_id": "2025-10-14-00-26-56",
#   "xform_bucket": "transform-data",
#   "prefix": "crash",
#   "gold_db_path": "/data/gold/gold.duckdb",
#   "gold_table": "gold.crashes"
# }


# docker exec -it cleaner python -c "
# import duckdb
# conn = duckdb.connect('/data/gold/gold.duckdb')
# print('Total crashes:', conn.execute('SELECT COUNT(*) FROM gold.crashes').fetchone()[0])
# print('Sample:', conn.execute('SELECT * FROM gold.crashes LIMIT 3').fetchall())
