# End-to-End Ride Analytics Data Pipeline

## 📋 Project Overview

A fully automated, production-grade data engineering pipeline for processing ride-sharing data (Uber-style), integrating batch pipelines, real-time analytics APIs, CI/CD automation, and conversational AI agents. The system includes robust data quality validation and PySpark unit testing using PyTest with coverage reporting, demonstrating real-world data engineering practices on Google Cloud Platform.

---

## 🏗️ Architecture Overview

<p align="center">
  <img src="images/architecture.jpeg" alt="Ride Analytics Architecture Diagram" width="900"/>
</p>

<p align="center">
  <em>End-to-end data pipeline architecture including ingestion, processing, API layer, and chatbot integration</em>
</p>

---

## 📊 Data Flow

### 1. **Data Generation (Mock Data)**

- **Script**:Mock ride-sharing data generated using `generate_sample_data.py`, simulating real-world ride-sharing activity in **Frankfurt am Main**
- **Simulation Features**:
  - Drivers, passengers, and rides
  - Geospatial data (coordinates)
  - Peak-hour demand patterns
  - Surge pricing behavior
  - Data quality issues for testing

<p align="center">
  <img src="docs/images/mockData.jpeg" alt=" " width="900"/>
</p>

<p align="center">
  <em>Raw ride-sharing data stored in the Bronze layer within Google Cloud Storage</em>
</p>

### 1. **Data Ingestion (Bronze Layer)**

- **Source**: Daily CSV/JSON files (rides, drivers, passengers)
- **Data Generation**: Mock ride-sharing data generated using `generate_sample_data.py`, simulating real-world scenarios for **Frankfurt am Main** (including neighborhoods, ride patterns, pricing, and peak-hour behavior)
- **Destination**: Single GCS Bucket with folders (`gs://ride-analytics/bronze/`)
  - `bronze/drivers/drivers.csv`
  - `bronze/passengers/passengers.csv`
  - `bronze/rides/YYYY-MM-DD/rides.csv`
- **Process**: Airflow DAG triggers on schedule, uploads raw files
- **Format**: Preserve original format with metadata (timestamp, source)

<p align="center">
  <img src="docs/images/bronze.jpeg" alt="Bronze Layer - Data Ingestion in GCS" width="900"/>
</p>

<p align="center">
  <em>Raw ride-sharing data stored in the Bronze layer within Google Cloud Storage</em>
</p>

### 2. **Data Quality Checks**

- **Framework**: Great Expectations or custom PySpark validations
- **Checks**:
  - Schema validation
  - Null checks on critical fields (ride_id, driver_id, passenger_id)
  - Data type validation
  - Business rule validation (e.g., ride_fare > 0, distance > 0, duration > 0)
  - Geographic validation (valid lat/long coordinates)
  - Duplicate detection
- **Action**: Fail pipeline if quality checks fail, send alerts

<p align="center">
  <img src="docs/images/qualityReport.jpeg" alt="Data quality validation report" width="900"/>
</p>

<p align="center">
  <em>Example data quality validation output from PySpark checks on Bronze-layer data</em>
</p>

### 3. **Data Processing (Silver Layer)**

- **Engine**: PySpark on Dataproc
- **Transformations**:
  - Data cleaning and standardization
  - Join operations (rides + drivers + passengers)
  - Calculate derived fields:
    - Ride distance (Haversine formula for pickup/dropoff coordinates)
    - Ride duration (from timestamps)
    - Fare per mile/km
    - Surge multiplier impact
  - Geospatial enrichment (city, zone from coordinates)
  - Time-based features (hour, day_of_week, is_peak_hour)
- **Output**: Parquet files in GCS (`gs://ride-analytics/silver/`)
  - `silver/rides_processed/`
  - `silver/drivers_processed/`
  - `silver/passengers_processed/`
- **Partitioning**: By date (year/month/day)

<p align="center">
  <img src="docs/images/silver.jpeg" alt="Silver layer processed dataset" width="900"/>
</p>

<p align="center">
  <em>Processed and cleaned dataset in the Silver layer after data quality validation</em>
</p>

### 4. **Data Warehouse (Gold Layer)**

- **Destination**: BigQuery
- **Tables**:
  - `fact_rides` - Ride transactions
  - `dim_drivers` - Driver master (SCD Type 2)
  - `dim_passengers` - Passenger master (SCD Type 2)
  - `agg_daily_rides` - Daily ride aggregations
  - `agg_driver_performance` - Driver analytics (ratings, earnings, trips)
  - `agg_demand_patterns` - Hourly/daily demand by location
  - `agg_revenue_metrics` - Revenue analytics by time and location

<p align="center">
  <img src="docs/images/gold.jpeg" alt="Gold layer aggregated dataset" width="900"/>
</p>

<p align="center">
  <em>Aggregated and business-ready dataset in the Gold layer for analytics and reporting</em>
</p>

### 5. **API Layer (FastAPI on Cloud Run)**

- **Purpose**: Serve processed ride analytics via a scalable, production-ready REST API

- **Endpoints**:
  - `/api/rides/daily` - Get daily ride metrics (count, revenue, avg duration)
  - `/api/drivers/{driver_id}` - Get driver performance and earnings
  - `/api/revenue/summary` - Get revenue summary by date range
  - `/api/health` - Health check endpoint

- **Features**:
  - High-performance API built using FastAPI
  - Real-time query execution on analytics data
  - Structured JSON responses for downstream systems
  - Health monitoring endpoint for service validation

- **Deployment**:
  - Containerized using Docker
  - Deployed on Google Cloud Run via CI/CD pipeline
  - Automatically scales based on incoming requests
  - Publicly accessible endpoint

- **Integration**:
  - Connects to data warehouse (Gold layer)
  - Serves as the central interface for external systems and automation tools

<p align="center">
  <img src="docs/images/api.jpeg" alt="FastAPI driver analytics endpoint response" width="900"/>
</p>

<p align="center">
  <em>Example response from the <code>/api/drivers/DRV000765</code> endpoint</em>
</p>

### 6. **Automation & Notification Layer (n8n + Telegram Bot)**

- **Purpose**: Automate workflows and provide real-time notifications based on pipeline events and analytics

- **Components**:
  - Workflow automation using n8n
  - Telegram Bot for messaging and alerts

- **Features**:
  - Event-driven and scheduled workflow execution
  - Automated alerts for Key metrics (e.g., daily revenue summaries)
  - Ability to trigger workflows based on API responses
  - Supports webhook-based integrations

- **Integration**:
  - Fetches data from FastAPI endpoints
  - Sends processed insights directly to users via Telegram
  - Can be extended to integrate with additional services (email, Slack, etc.)

- **Deployment**:
  - Runs as a separate service (cloud-based)
  - Configurable via environment variables and webhook triggers

<p align="center">
  <img src="docs/images/bot.jpeg" alt="n8n Telegram bot workflow pipeline" width="900"/>
</p>

<p align="center">
  <em>n8n workflow pipeline for Telegram bot automation and API integration</em>
</p>

<p align="center">
  <img src="docs/images/botResponse.jpeg" alt="Telegram bot daily analytics response" width="900"/>
</p>

<p align="center">
  <em>Example Telegram bot response for the <code>/daily 2026-05-04</code> analytics request</em>
</p>

**Note:** The orchestration layer was implemented using Apache Airflow and designed to support managed orchestration platforms such as Google Cloud Composer. Due to infrastructure cost constraints, DAG execution and validation were performed in a development/testing environment rather than a managed Composer deployment.

---

## 🛠️ Tech Stack

| Component         | Technology                      | Purpose                                               |
| ----------------- | ------------------------------- | ----------------------------------------------------- | --- |
| **Orchestration** | Apache Airflow                  | Workflow scheduling and pipeline orchestration        |
| **Processing**    | PySpark (Databricks / Dataproc) | Distributed data transformation and processing        |
| **Storage**       | Google Cloud Storage (GCS)      | Data lake storage for Bronze and Silver layers        |
| **Warehouse**     | BigQuery                        | Analytics and reporting layer (Gold layer)            |
| **API**           | FastAPI + Cloud Run             | Scalable REST API for serving analytics data          |
| **Automation**    | n8n + Telegram Bot              | Workflow automation and real-time notifications       |
| **CI/CD**         | GitHub Actions                  | Automated testing, validation, and deployment         |
| **Testing**       | pytest + PySpark Testing        | Unit and integration testing                          |
| **Data Quality**  | Custom PySpark Validations      | Data quality validation and business rule enforcement |     |

---

## 📁 Project Structure

```
Ride-Analytics-Project/
├── README.md                       # Project overview and architecture
├── SETUP.md                        # Setup and deployment guide
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI pipeline (tests, linting)
│       └── deploy.yml             # CD pipeline (deploy to GCP)
├── airflow/
│   ├── dags/
│   │   └── rides_pipeline_dag.py  # Main Airflow DAG
│   └── requirements.txt
├── spark/
│   ├── jobs/
│   │   ├── bronze_to_silver.py    # Spark transformation job
│   │   ├── silver_to_gold.py      # BigQuery load job
│   │   └── data_quality.py        # Data quality checks
│   ├── tests/
│   │   └── test_transformations.py
│   └── requirements.txt
├── api/
│   ├── main.py                    # FastAPI application
│   ├── Dockerfile                 # Container definition
│   └── requirements.txt
└── scripts/
    ├── generate_sample_data.py    # Realistic data generation
    ├── requirements.txt
    └── data/                      # Generated sample data
        └── raw/
```

---

## 🔄 Pipeline Process Flow

### Daily Execution Flow

1. **00:00 UTC - Data Arrival**
   - New ride data files arrive in source system
   - Airflow DAG triggers automatically

2. **00:05 UTC - Data Ingestion (Bronze)**
   - Airflow task: `ingest_raw_data`
   - Upload ride/driver/passenger files to GCS Bronze bucket
   - Log ingestion metadata

3. **00:10 UTC - Data Quality Validation**
   - Airflow task: `run_data_quality_checks`
   - Execute PySpark data quality job
   - Validate schema, nulls, business rules, geospatial data
   - **If FAIL**: Send alert, stop pipeline
   - **If PASS**: Continue to processing

4. **00:20 UTC - Data Processing (Silver)**
   - Airflow task: `process_silver_layer`
   - Submit PySpark job to Dataproc
   - Transform and clean data
   - Calculate distances, durations, fare metrics
   - Enrich with geospatial and time features
   - Write to GCS Silver bucket (Parquet)

5. **00:40 UTC - Load to BigQuery (Gold)**
   - Airflow task: `load_to_bigquery`
   - Load Parquet files to BigQuery tables
   - Update dimension tables (SCD Type 2 for drivers/passengers)
   - Create aggregated tables (daily rides, driver performance, demand patterns)

6. **00:50 UTC - API & Notification Layer**
   - FastAPI serves processed analytics through REST endpoints
   - n8n workflows trigger automated notifications
   - Telegram bot delivers analytics summaries and pipeline alerts

---

### Idempotency

- All jobs are idempotent (can re-run safely)
- Use date partitions to avoid duplicate processing
- Upsert logic in BigQuery (merge statements)

---

## 🧪 Testing Strategy

### Unit Tests (PySpark)

- Test individual transformation functions
- Mock Spark DataFrames
- Test data quality validation logic
- Test edge cases (nulls, empty data)

### Integration Tests

- Test end-to-end pipeline with sample data
- Test Airflow DAG with test environment

### Test Coverage

- Target: 80%+ code coverage using pytest
- Focus on business logic and transformations
- Test error handling paths

### CI/CD Testing

- Run tests on every PR
- Run integration tests before deployment
- Fail build if tests fail

---

## 🔄 CI/CD Pipeline (GitHub Actions)

This project has two GitHub Actions workflows. See [`.github/workflows/README.md`](.github/workflows/README.md) for detailed explanation.

### Quick Overview:

#### **1. CI Pipeline** (`ci.yml`) - Continuous Integration

**Triggers:** Every push and pull request

**Jobs (run in parallel):**

- ✅ **Lint** - Check code quality (flake8, black)
- ✅ **Test Spark** - Run PySpark unit tests with coverage
- ✅ **Validate Airflow** - Check DAG syntax

**Purpose:** Validate code quality before merging/deployment

#### **2. CD Pipeline** (`deploy.yml`) - Continuous Deployment

**Triggers:** Push to `main` branch or manual trigger

**Steps:**

1. Authenticate to GCP
2. Upload Spark jobs to GCS (`gs://bucket/spark-jobs/`)
3. Upload Airflow DAGs to Composer
4. Verify GCP resources (bucket, Dataproc, BigQuery)

**Purpose:** Deploy code to GCP automatically

### Workflow Flow:

```
Push Code → CI Pipeline Runs → Tests Pass? → Merge to main → CD Pipeline Runs → Deployed to GCP
                ↓
           Tests Fail? → Fix Issues → Push Again
```

**Note:**

- CI runs on every push/PR (validates code)
- CD runs only on `main` branch (deploys code)

**For detailed explanation:** See [`.github/workflows/README.md`](.github/workflows/README.md)

---

## 📋 Data Schema

### Bronze Layer (Raw Data)

**rides.csv**

```
ride_id, driver_id, passenger_id, pickup_datetime, dropoff_datetime,
pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
fare_amount, tip_amount, surge_multiplier, ride_status
```

**drivers.csv**

```
driver_id, name, email, phone, registration_date, vehicle_type,
license_plate, city, rating, is_active
```

**passengers.csv**

```
passenger_id, name, email, phone, registration_date, city,
preferred_payment_method, rating
```

### Silver Layer (Processed)

**rides_processed** (Parquet)

- All bronze fields + calculated fields
- ride_distance_km, ride_duration_minutes, fare_per_km
- pickup_hour, pickup_day_of_week, is_peak_hour
- Data types standardized
- Nulls handled

### Gold Layer (BigQuery)

**fact_rides**

- Ride transaction facts

**dim_drivers** (SCD Type 2)

- Driver dimension with history
- effective_date, end_date, is_current

**dim_passengers** (SCD Type 2)

- Passenger dimension with history
- effective_date, end_date, is_current

**agg_daily_rides**

- Daily aggregated rides
- total_rides, total_revenue, avg_duration, avg_distance

**agg_driver_performance**

- Driver performance metrics
- total_trips, total_earnings, avg_rating, completion_rate

**agg_demand_patterns**

- Demand patterns by hour and location
- ride_count, avg_surge_multiplier, total_revenue

---

## 📝 Next Steps

1. **Introduce Real-Time Data Streaming**
   - Integrate event streaming using tools like Kafka or Pub/Sub
   - Ingest ride events in real-time instead of batch CSV uploads
   - Process streaming data using Spark Structured Streaming
   - Enable near real-time analytics for ride activity

2. **Enhance FastAPI Service**
   - Add authentication and rate limiting
   - Improve query optimization and caching
   - Add monitoring and observability
   - Expand analytics endpoints

3. **Production-Ready Deployment**
   - Add environment-based configurations (dev/staging/prod)
   - Improve CI/CD with selective deployments and safeguards
   - Containerize services and optimize resource usage
   - Introduce rollback and failure recovery strategies

---

## 📚 Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Cloud Monitoring](https://cloud.google.com/monitoring/docs)

---

**Author**: Amber Asad  
**Last Updated**: 2026-05-06
