#!/bin/bash
# Cloud Composer Deployment Script
# Run: bash cloud-composer/deploy.sh

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-rh-etl-project-467521}"
LOCATION="europe-west1"
COMPOSER_ENV="mmm-composer"
DATASET="MMM_datset"
TABLE="mmm"

echo "=== Cloud Composer Deployment Script ==="
echo "Project: $PROJECT_ID"
echo "Location: $LOCATION"
echo "Environment: $COMPOSER_ENV"
echo ""

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not found. Install it first: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "[1/6] Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "[2/6] Enabling required APIs..."
gcloud services enable composer.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com

# Create service account
echo "[3/6] Creating service account..."
SA_EMAIL="cloud-composer-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_EMAIL 2>/dev/null; then
    echo "Service account already exists"
else
    gcloud iam service-accounts create cloud-composer-sa \
        --display-name="Cloud Composer Service Account"
fi

# Assign roles
echo "[4/6] Assigning IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SA_EMAIL \
    --role=roles/bigquery.dataEditor \
    --condition=None
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SA_EMAIL \
    --role=roles/bigquery.jobUser \
    --condition=None
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$SA_EMAIL \
    --role=roles/storage.objectAdmin \
    --condition=None

# Create Cloud Composer environment
echo "[5/6] Creating Cloud Composer environment (this may take 10-15 minutes)..."
if gcloud composer environments describe $COMPOSER_ENV --location $LOCATION 2>/dev/null; then
    echo "Environment already exists"
else
    gcloud composer environments create $COMPOSER_ENV \
        --location $LOCATION \
        --python-version 3 \
        --machine-type n1-standard-4 \
        --node-count 3 \
        --env-variables \
            GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
            BIGQUERY_DATASET=$DATASET,\
            BIGQUERY_TABLE=$TABLE
fi

# Copy DAG and repo
echo "[6/6] Deploying DAG and repository..."
BUCKET=$(gcloud composer environments describe $COMPOSER_ENV \
    --location $LOCATION \
    --format="value(config.dagGcsPrefix)" | sed 's/\/dags$//')

# Copy DAG
gsutil cp cloud-composer/mmm_pipeline_gcp.py gs://${BUCKET}/dags/

# Optional: Copy entire repo (for use in PythonOperator)
echo "Packaging and uploading repository..."
tar -czf /tmp/mmm_repo.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.env' \
    --exclude='venv' \
    --exclude='airflow' \
    .
gsutil cp /tmp/mmm_repo.tar.gz gs://${BUCKET}/data/

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Access Airflow UI:"
echo "  Console: https://console.cloud.google.com/composer/environments/detail/$LOCATION/$COMPOSER_ENV/dags"
echo "  Or via CLI: gcloud composer environments run $COMPOSER_ENV --location $LOCATION web-server"
echo ""
echo "Trigger DAG manually:"
echo "  gcloud composer environments run $COMPOSER_ENV --location $LOCATION dags -- trigger mmm_pipeline_gcp"
echo ""
echo "Monitor logs:"
echo "  gcloud composer environments storage logs list --environment $COMPOSER_ENV --location $LOCATION"
echo ""
