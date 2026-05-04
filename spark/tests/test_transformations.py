import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from pyspark.sql.functions import col
import sys
import os

# Set Python path for Spark workers to match driver
# This ensures both driver and workers use the same Python version
python_exec = sys.executable
os.environ['PYSPARK_PYTHON'] = python_exec
os.environ['PYSPARK_DRIVER_PYTHON'] = python_exec

# Add parent directories to path so we can import from jobs module
# Test is in spark/tests/, so we need to go up to spark/, then up to project root
spark_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
project_root = os.path.abspath(os.path.join(spark_dir, '..'))
sys.path.insert(0, project_root)

# Import from spark.jobs module 
from spark.jobs.bronze_to_silver import (
    haversine_distance,
    transform_rides,
    transform_drivers,
    transform_passengers,
)

from spark.jobs.data_quality import (
    check_schema,
    check_uniqueness,
    check_nulls,
)

from spark.jobs.silver_to_gold import (
    create_fact_rides,
    create_agg_daily_rides,
)


# -------------------------
# Spark Fixture
# -------------------------
@pytest.fixture(scope="session")
def spark():
    """Create Spark session for testing"""
    import zipfile
    import tempfile
    
    # Ensure Python version consistency
    os.environ['PYSPARK_PYTHON'] = sys.executable
    os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
    
    # Get directory paths
    spark_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    project_root = os.path.abspath(os.path.join(spark_dir, '..'))
    jobs_dir = os.path.join(spark_dir, 'jobs')
    
    # Add project root to PYTHONPATH for driver
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    if current_pythonpath:
        os.environ['PYTHONPATH'] = f"{project_root}:{current_pythonpath}"
    else:
        os.environ['PYTHONPATH'] = project_root
    
    spark = SparkSession.builder \
        .appName("TestTransformations") \
        .master("local[2]") \
        .config("spark.sql.adaptive.enabled", "false") \
        .config("spark.python.worker.reuse", "false") \
        .config("spark.executorEnv.PYTHONPATH", project_root) \
        .getOrCreate()
    
    # Create a zip file of the spark directory and add it to Spark
    # This ensures workers can import spark.jobs.bronze_to_silver
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        zip_path = tmp_zip.name
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all Python files from spark directory
            for root, dirs, files in os.walk(spark_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        # Archive path should maintain directory structure
                        arcname = os.path.relpath(file_path, project_root)
                        zipf.write(file_path, arcname)
        
        # Add the zip file to Spark so workers can import from it
        spark.sparkContext.addPyFile(zip_path)
    
    yield spark
    spark.stop()
    
    # Clean up temporary zip file
    try:
        os.unlink(zip_path)
    except:
        pass



# -------------------------
# Sample Data
# -------------------------
@pytest.fixture
def sample_rides_data(spark):
    schema = StructType([
        StructField("ride_id", StringType(), True),
        StructField("driver_id", StringType(), True),
        StructField("passenger_id", StringType(), True),
        StructField("pickup_datetime", StringType(), True),
        StructField("dropoff_datetime", StringType(), True),
        StructField("pickup_latitude", StringType(), True),
        StructField("pickup_longitude", StringType(), True),
        StructField("dropoff_latitude", StringType(), True),
        StructField("dropoff_longitude", StringType(), True),
        StructField("fare_amount", StringType(), True),
        StructField("tip_amount", StringType(), True),
        StructField("surge_multiplier", StringType(), True),
        StructField("ride_status", StringType(), True),
    ])

    data = [
    # Innenstadt → Sachsenhausen (~2–3 km)
        ("RIDE001", "DRV001", "PAS001", "2026-01-15 10:00:00", "2026-01-15 10:30:00",
        "50.1109", "8.6821", "50.1047", "8.6837", "12.50", "2.00", "1.0", "completed"),

        # Bockenheim → Flughafen (~10 km)
        ("RIDE002", "DRV002", "PAS002", "2026-01-15 11:00:00", "2026-01-15 11:25:00",
        "50.1193", "8.6466", "50.0379", "8.5622", "28.00", "0.00", "1.3", "completed"),
    ]

    return spark.createDataFrame(data, schema)


# -------------------------
# Data Quality Tests
# -------------------------
def test_check_schema(spark):
    """Test schema validation"""
    df = spark.createDataFrame([("1",)], ["ride_id"])
    
    passed, missing = check_schema(df, ["ride_id", "driver_id"])
    
    assert passed is False
    assert "driver_id" in missing


def test_check_uniqueness(spark):
    """Test duplicate detection"""
    df = spark.createDataFrame([
        ("RIDE001",),
        ("RIDE001",),
    ], ["ride_id"])
    
    result = check_uniqueness(df, "ride_id")
    
    assert result["duplicate_count"] == 1


def test_check_nulls(spark):
    """Test null checks"""
    df = spark.createDataFrame([
        (None,),
        ("RIDE002",),
    ], ["ride_id"])
    
    result = check_nulls(df, ["ride_id"])
    
    assert "ride_id" in result
    assert result["ride_id"] > 0


# -------------------------
# Bronze → Silver Tests
# -------------------------
def test_haversine_valid():
    """Test Haversine distance calculation (Frankfurt)"""
    
    # Frankfurt Innenstadt → Flughafen (~10–12 km)
    lat1, lon1 = 50.1109, 8.6821
    lat2, lon2 = 50.0379, 8.5622
    
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    
    assert distance is not None
    assert 8 < distance < 15

def test_haversine_invalid():
    """Test Haversine distance with invalid inputs"""
    distance = haversine_distance(None, None, None, None)
    assert distance is None

def test_transform_rides(spark, sample_rides_data):
    """Test rides transformation"""
    from spark.jobs.bronze_to_silver import transform_rides
    
    transformed_df = transform_rides(spark, sample_rides_data)
    
    # Check that new columns are created
    assert "ride_distance_km" in transformed_df.columns
    assert "ride_duration_minutes" in transformed_df.columns
    assert "fare_per_km" in transformed_df.columns
    assert "total_fare" in transformed_df.columns
    assert "pickup_hour" in transformed_df.columns
    assert "pickup_day_of_week" in transformed_df.columns
    assert "is_peak_hour" in transformed_df.columns
    
    # Check data types
    assert transformed_df.schema["ride_distance_km"].dataType == DoubleType()
    assert transformed_df.schema["total_fare"].dataType == DoubleType()
    
    # Check that records are processed
    assert transformed_df.count() == 2


def test_transform_rides_nulls(spark):
    """Test rides transformation with null values"""
    from spark.jobs.bronze_to_silver import transform_rides
    
    schema = StructType([
        StructField("ride_id", StringType(), True),
        StructField("driver_id", StringType(), True),
        StructField("passenger_id", StringType(), True),
        StructField("pickup_datetime", StringType(), True),
        StructField("dropoff_datetime", StringType(), True),
        StructField("pickup_latitude", StringType(), True),
        StructField("pickup_longitude", StringType(), True),
        StructField("dropoff_latitude", StringType(), True),
        StructField("dropoff_longitude", StringType(), True),
        StructField("fare_amount", StringType(), True),
        StructField("tip_amount", StringType(), True),
        StructField("surge_multiplier", StringType(), True),
        StructField("ride_status", StringType(), True),
    ])
    
    data = [
        ("RIDE001", "DRV001", "PAS001", "2025-01-15 10:00:00", None,
         None, None, None, None, None, None, "1.0", "cancelled"),
    ]
    
    df = spark.createDataFrame(data, schema)
    transformed_df = transform_rides(spark, df)
    
    # Should handle nulls gracefully
    assert transformed_df.count() == 1
    assert transformed_df.filter(col("ride_distance_km").isNull()).count() == 1


def test_transform_drivers(spark):
    data = [("D1","John","mail","123","2025-01-01","car","ABC","Frankfurt","4.5","True")]
    cols = ["driver_id","name","email","phone","registration_date","vehicle_type","license_plate","city","rating","is_active"]

    df = spark.createDataFrame(data, cols)
    result = transform_drivers(df)

    assert "processed_timestamp" in result.columns
    assert result.count() == 1


def test_transform_passengers(spark):
    data = [("P1","Alice","mail","123","2025-01-01","Frankfurt","card","4.2")]
    cols = ["passenger_id","name","email","phone","registration_date","city","preferred_payment_method","rating"]

    df = spark.createDataFrame(data, cols)
    result = transform_passengers(df)

    assert "processed_timestamp" in result.columns


# -------------------------
# Silver → Gold Tests
# -------------------------
def test_create_fact_rides(spark, sample_rides_data):
    """Test fact table creation"""
    from spark.jobs.silver_to_gold import create_fact_rides
    
    silver_df = transform_rides(spark, sample_rides_data)
    fact_df = create_fact_rides(spark, silver_df)
    
    # Check columns exist
    assert "ride_id" in fact_df.columns
    assert "driver_id" in fact_df.columns
    assert "passenger_id" in fact_df.columns
    
    # Ensure data exists
    assert fact_df.count() == 2


def test_agg_daily_rides(spark, sample_rides_data):
    """Test daily aggregation"""
    from spark.jobs.silver_to_gold import create_agg_daily_rides
    
    silver_df = transform_rides(spark, sample_rides_data)
    agg_df = create_agg_daily_rides(spark, silver_df)
    
    # Check aggregation columns
    assert "total_rides" in agg_df.columns
    assert "total_revenue" in agg_df.columns
    
    # Ensure aggregation works
    assert agg_df.count() >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
