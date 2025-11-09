import pandas as pd
from minio_io import download_silver_csv
import logging

# ---------------------------------
# Logging
# ---------------------------------
logging.basicConfig(level=logging.INFO, format="[cleaner.cleaning_rules] %(message)s")


def clean_data(corr_id: str) -> pd.DataFrame:
    """
    Apply all cleaning rules to Silver CSV data to produce Gold-ready DataFrame.

    Args:
        corr_id: Correlation ID for the data run to clean

    Returns:
        pd.DataFrame: Cleaned DataFrame ready for Gold layer
    """
    logging.info(f"Starting data cleaning for corr_id={corr_id}")

    # Download Silver CSV from MinIO
    df = download_silver_csv(corr_id)
    logging.info(f"Downloaded {len(df)} rows with {len(df.columns)} columns")

    # Step 1: Drop leakage and ID columns
    # Extract columns that we want and make an explicit copy
    # Confirm columns we want actually exist in df
    # Sometimes if all records that were extracted in a job are null for a certain value, that column will be left out
    req_cols = [
        'crash_record_id', 'beat_of_occurrence', 'crash_date', 'crash_day_of_week', 'crash_hour', 'crash_type', 
        'hit_and_run_i', 'num_units', 'injuries_total', 'lighting_condition', 'latitude', 'longitude', 
        'posted_speed_limit', 'road_defect', 'roadway_surface_cond', 'street_direction', 'trafficway_type', 
        'weather_condition', 'intersection_related_i', 'traffic_control_device', 'work_zone_i',
        'private_property_i'
    ]
    existing_cols = []
    add_cols = []
    df_cols = df.columns

    for col in req_cols:
        if col in df_cols:
            existing_cols.append(col)
        else:
            add_cols.append(col)

    df_clean = df[existing_cols].copy()
    # Init all columns that don't exist to none type
    for col in add_cols:
        df_clean[col] = None


    # Step 2: Standardize Boolean Columns
    # Convert Y/yes/true/1 -> 1, N/no/false/0 -> 0, everything else (including NaN) -> 0

    def standardize_boolean(value):
        """
        Standardize boolean-like values to 1 or 0.
        
        Args:
            value: Input value (could be string, int, float, etc.)
        
        Returns:
            1 or 0
        """
        if pd.isna(value):
            return 0
        
        # Convert to string and normalize
        val_str = str(value).strip().lower()
        
        # Map to 1 (True)
        if val_str in ['y', 'yes', 'true', 't', '1', '1.0']:
            return 1
        
        # Everything else (including N/no/false/0 and unknown values) becomes 0
        return 0

    # Apply to boolean columns
    bool_cols = ['hit_and_run_i', 'intersection_related_i', 'private_property_i', 'work_zone_i']

    for col in bool_cols:
        df_clean[col] = df_clean[col].apply(standardize_boolean)
        
    # Convert to regular integer type (no NaN values now)
    for col in bool_cols:
        df_clean[col] = df_clean[col].astype('int64')

    # Create is_weekend column
    # Sunday is 1, saturday is 7
    def is_weekend_col(val):
        if val == 1 or val == 7:
            return 1
        else:
            return 0
    df_clean['is_weekend'] = df_clean['crash_day_of_week'].apply(is_weekend_col)

    # Add hour_bin column
    def add_hour_bin(val):
        if val <= 6:
            return 'night'
        elif val <= 12:
            return 'morning'
        elif val <= 18:
            return 'afternoon'
        elif val <= 23:
            return 'evening'
        else:
            return None
        
    df_clean['hour_bin'] = df_clean['crash_hour'].apply(add_hour_bin)

    # Clean date
    # Drop nulls first: nothing to infer date from and cannot fill with median (would make no sense)
    df_clean = df_clean.dropna(subset=['crash_date'])

    # Convert to date time, normalize to get rid of seconds and time
    df_clean['crash_date'] = pd.to_datetime(df_clean['crash_date']).dt.normalize()


    # =========================================
    # =========================================

    # Chicago approximate bounding box
    # Latitude: ~41.64 to ~42.02
    # Longitude: ~-87.94 to ~-87.52
    CHICAGO_LAT_MIN = 41.6
    CHICAGO_LAT_MAX = 42.1
    CHICAGO_LNG_MIN = -88.0
    CHICAGO_LNG_MAX = -87.5

    # Identify invalid rows
    invalid_coords = (
        (df_clean['latitude'] == 0) & (df_clean['longitude'] == 0)  # (0, 0) coordinates
    ) | (
        (df_clean['latitude'] < CHICAGO_LAT_MIN) | (df_clean['latitude'] > CHICAGO_LAT_MAX)  # Outside Chicago lat
    ) | (
        (df_clean['longitude'] < CHICAGO_LNG_MIN) | (df_clean['longitude'] > CHICAGO_LNG_MAX)  # Outside Chicago lng
    )

    # Drop invalid rows
    df_clean = df_clean[~invalid_coords].copy()

    # Create binned latitude and longitude (rounded to 2 decimal places)
    df_clean['lat_bin'] = df_clean['latitude'].round(2)
    df_clean['lng_bin'] = df_clean['longitude'].round(2)

    # Create grid_id by combining lat_bin and lng_bin
    df_clean['grid_id'] = df_clean['lat_bin'].astype(str) + '_' + df_clean['lng_bin'].astype(str)

    # Clean roadway_surface_cond
    valid_roadway = ['DRY', 'UNKNOWN', 'WET', 'SNOW OR SLUSH', 'ICE']
    df_clean['roadway_surface_cond'] = df_clean['roadway_surface_cond'].str.upper()
    df_clean.loc[~df_clean['roadway_surface_cond'].isin(valid_roadway), 'roadway_surface_cond'] = 'OTHER'

    # Clean lighting_condition
    valid_lighting = ['DARKNESS, LIGHTED ROAD', 'UNKNOWN', 'DARKNESS', 'DAWN', 'DAYLIGHT', 'DUSK']
    df_clean['lighting_condition'] = df_clean['lighting_condition'].str.upper()
    df_clean.loc[~df_clean['lighting_condition'].isin(valid_lighting), 'lighting_condition'] = 'OTHER'

    # Consolidate weather_condition
    df_clean['weather_condition'] = df_clean['weather_condition'].str.upper()

    # Map snow-related conditions to SNOW
    snow_conditions = ['SNOW', 'BLOWING SNOW', 'SLEET/HAIL', 'FREEZING RAIN/DRIZZLE']
    df_clean.loc[df_clean['weather_condition'].isin(snow_conditions), 'weather_condition'] = 'SNOW'

    # Keep common conditions, map others to OTHER
    valid_weather = ['CLOUDY/OVERCAST', 'CLEAR', 'RAIN', 'SNOW']
    df_clean.loc[~df_clean['weather_condition'].isin(valid_weather), 'weather_condition'] = 'OTHER'

    # Clean traffic_control_device
    valid_traffic = ['NO CONTROLS', 'TRAFFIC SIGNAL', 'STOP SIGN/FLASHER', 'UNKNOWN']
    df_clean['traffic_control_device'] = df_clean['traffic_control_device'].str.upper()
    df_clean.loc[~df_clean['traffic_control_device'].isin(valid_traffic), 'traffic_control_device'] = 'OTHER'

    # Clean crash_type
    valid_crash_type = ['NO INJURY / DRIVE AWAY', 'INJURY AND / OR TOW DUE TO CRASH']
    df_clean['crash_type'] = df_clean['crash_type'].str.upper()
    df_clean.loc[~df_clean['crash_type'].isin(valid_crash_type), 'crash_type'] = 'OTHER'

    # =========================================
    # =========================================

    # Step 8: Handle Missing Values

    # Exception: injuries_total nulls -> 0 (no injuries reported)
    df_clean['injuries_total'] = df_clean['injuries_total'].fillna(0)

    # Handle numeric columns with median
    numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns.tolist()
    # Exclude crash_record_id if it's in there, and columns already handled
    numeric_cols = [col for col in numeric_cols if col not in ['crash_record_id', 'injuries_total', 
                                                                'hit_and_run_i', 'intersection_related_i', 
                                                                'private_property_i', 'work_zone_i', 'is_weekend']]

    for col in numeric_cols:
        if df_clean[col].isna().sum() > 0:
            median_val = df_clean[col].median()
            print(f"{col}: {df_clean[col].isna().sum()} nulls -> filling with median = {median_val}")
            df_clean[col] = df_clean[col].fillna(median_val)

    # Handle categorical columns with 'OTHER'
    categorical_cols = df_clean.select_dtypes(include=['object']).columns.tolist()
    # Exclude crash_record_id (identifier)
    categorical_cols = [col for col in categorical_cols if col != 'crash_record_id']

    for col in categorical_cols:
        if df_clean[col].isna().sum() > 0:
            print(f"{col}: {df_clean[col].isna().sum()} nulls -> filling with 'OTHER'")
            df_clean[col] = df_clean[col].fillna('OTHER')


    # ====================================================
    # ====================================================
    # Step 9: Cap Outliers
    # Cap number of units involved at 10
    df_clean.loc[df_clean['num_units'] > 10, 'num_units'] = 10

    # Cap posted speed limit at 75 mph
    df_clean.loc[df_clean['posted_speed_limit'] > 75, 'posted_speed_limit'] = 75

    return df_clean