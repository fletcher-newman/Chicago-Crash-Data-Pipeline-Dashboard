# cleaner/minio_io.py
import os
import io
import logging
from typing import Optional

import pandas as pd
from minio import Minio
from minio.error import S3Error

# ---------------------------------
# Logging
# ---------------------------------
logging.basicConfig(level=logging.INFO, format="[cleaner.minio_io] %(message)s")

# ---------------------------------
# MinIO Configuration
# ---------------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_USER", "admin")
MINIO_SECRET = os.getenv("MINIO_PASS", "admin123")
MINIO_SECURE = os.getenv("MINIO_SSL", "false").lower() == "true"


def get_minio_client(endpoint: Optional[str] = None) -> Minio:
    """
    Create and return a MinIO client instance.

    Args:
        endpoint: Override MinIO endpoint (useful for testing from host vs Docker)
                 If None, uses MINIO_ENDPOINT env var or defaults to localhost:9000

    Returns:
        Minio: Configured MinIO client

    Raises:
        ValueError: If required environment variables are missing
    """
    # Allow override for testing from host machine
    minio_endpoint = endpoint or MINIO_ENDPOINT

    # Auto-replace 'minio' hostname with 'localhost' ONLY when running outside Docker
    # Check if we're in a Docker container by looking for /.dockerenv or checking cgroup
    in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')

    if minio_endpoint.startswith("minio:") and not in_docker:
        # Running on host machine (e.g., testing in notebook) - use localhost
        minio_endpoint = minio_endpoint.replace("minio:", "localhost:", 1)
        logging.info(f"Replaced 'minio' with 'localhost' for host-based testing")
    # else: Running in Docker - keep 'minio' hostname (Docker network resolution)

    if not minio_endpoint or not MINIO_ACCESS or not MINIO_SECRET:
        raise ValueError(
            "Missing MinIO configuration. Ensure MINIO_ENDPOINT, "
            "MINIO_USER, and MINIO_PASS are set in environment."
        )

    logging.info(
        f"MinIO config: endpoint={minio_endpoint}, "
        f"secure={MINIO_SECURE}, access={MINIO_ACCESS}"
    )

    return Minio(
        endpoint=minio_endpoint,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=MINIO_SECURE,
    )


def download_silver_csv(
    corr_id: str,
    bucket: str = "transform-data",
    prefix: str = "crash"
) -> pd.DataFrame:
    """
    Download the Silver CSV for a given correlation ID from MinIO.

    The expected path is: {bucket}/{prefix}/corr={corr_id}/merged.csv

    Args:
        corr_id: Correlation ID from the transform job (e.g., "2025-09-29T16-12-01Z")
        bucket: MinIO bucket name (default: "transform-data")
        prefix: Object key prefix (default: "crash")

    Returns:
        pd.DataFrame: Loaded Silver data

    Raises:
        FileNotFoundError: If the Silver CSV does not exist in MinIO
        S3Error: If there's an error communicating with MinIO
        ValueError: If the CSV is empty or malformed
    """
    client = get_minio_client()

    # Construct the object key
    object_key = f"{prefix}/corr={corr_id}/merged.csv"

    logging.info(f"Attempting to download: s3://{bucket}/{object_key}")

    # Check if object exists
    try:
        stat = client.stat_object(bucket_name=bucket, object_name=object_key)
        logging.info(f"Found object: size={stat.size} bytes, last_modified={stat.last_modified}")
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise FileNotFoundError(
                f"Silver CSV not found at s3://{bucket}/{object_key}. "
                f"Ensure the Transformer has completed for corr_id={corr_id}"
            )
        else:
            raise

    # Download the object
    response = None
    try:
        response = client.get_object(bucket_name=bucket, object_name=object_key)
        data = response.read()

        # Load into pandas DataFrame
        df = pd.read_csv(io.BytesIO(data))

        logging.info(f"Downloaded Silver CSV: {len(df)} rows, {len(df.columns)} columns")

        if df.empty:
            raise ValueError(f"Silver CSV at s3://{bucket}/{object_key} is empty")

        return df

    finally:
        # Always clean up the response
        if response is not None:
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass



if __name__ == "__main__":
    # Example usage / testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python minio_io.py <corr_id>")
        print("Example: python minio_io.py 2025-09-29T16-12-01Z")
        sys.exit(1)

    test_corr_id = sys.argv[1]

    try:
        df = download_silver_csv(test_corr_id)
        print(f"\nSuccessfully downloaded Silver CSV for corr_id={test_corr_id}")
        print(f"Shape: {df.shape}")
        print(f"\nFirst few rows:")
        print(df.head())
        print(f"\nColumns: {list(df.columns)}")
    except Exception as e:
        logging.error(f"Failed to download: {e}")
        raise
