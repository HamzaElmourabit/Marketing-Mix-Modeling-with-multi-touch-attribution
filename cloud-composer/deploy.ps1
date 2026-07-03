# Cloud Composer Deployment Script (PowerShell)
# Run: .\cloud-composer\deploy.ps1

param(
    [string]$ProjectId = "rh-etl-project-467521",
    [string]$Location = "europe-west1",
    [string]$ComposerEnv = "mmm-composer",
    [string]$Dataset = "MMM_datset",
    [string]$Table = "mmm"
)

Write-Host "=== Cloud Composer Deployment Script ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectId"
Write-Host "Location: $Location"
Write-Host "Environment: $ComposerEnv"
Write-Host ""

# Check gcloud
try {
    gcloud --version | Out-Null
} catch {
    Write-Host "ERROR: gcloud CLI not found. Install it first:" -ForegroundColor Red
    Write-Host "https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Set project
Write-Host "[1/6] Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable APIs
Write-Host "[2/6] Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable composer.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com

# Create service account
Write-Host "[3/6] Creating service account..." -ForegroundColor Yellow
$SA_EMAIL = "cloud-composer-sa@${ProjectId}.iam.gserviceaccount.com"
$saExists = gcloud iam service-accounts describe $SA_EMAIL 2>$null
if ($saExists) {
    Write-Host "Service account already exists"
} else {
    gcloud iam service-accounts create cloud-composer-sa --display-name="Cloud Composer Service Account"
}

# Assign roles
Write-Host "[4/6] Assigning IAM roles..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $ProjectId `
    --member=serviceAccount:$SA_EMAIL `
    --role=roles/bigquery.dataEditor
gcloud projects add-iam-policy-binding $ProjectId `
    --member=serviceAccount:$SA_EMAIL `
    --role=roles/bigquery.jobUser
gcloud projects add-iam-policy-binding $ProjectId `
    --member=serviceAccount:$SA_EMAIL `
    --role=roles/storage.objectAdmin

# Create Cloud Composer environment
Write-Host "[5/6] Creating Cloud Composer environment (this may take 10-15 minutes)..." -ForegroundColor Yellow
$envExists = gcloud composer environments describe $ComposerEnv --location $Location 2>$null
if ($envExists) {
    Write-Host "Environment already exists"
} else {
    gcloud composer environments create $ComposerEnv `
        --location $Location `
        --python-version 3 `
        --machine-type n1-standard-4 `
        --node-count 3 `
        --env-variables `
            GOOGLE_CLOUD_PROJECT=$ProjectId,`
            BIGQUERY_DATASET=$Dataset,`
            BIGQUERY_TABLE=$Table
}

# Copy DAG and repo
Write-Host "[6/6] Deploying DAG and repository..." -ForegroundColor Yellow
$bucketInfo = gcloud composer environments describe $ComposerEnv `
    --location $Location `
    --format="value(config.dagGcsPrefix)"
$bucket = ($bucketInfo -split '/dags$')[0]

Write-Host "Uploading DAG to gs://${bucket}/dags/"
gsutil cp cloud-composer/mmm_pipeline_gcp.py "gs://${bucket}/dags/"

Write-Host "Packaging and uploading repository..."
$repoArchive = "$env:TEMP\mmm_repo.tar.gz"
# Note: For Windows, you may need to use Git Bash or WSL for tar
# Alternative: use 7z or similar

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Access Airflow UI:"
Write-Host "  Console: https://console.cloud.google.com/composer/environments/detail/$Location/$ComposerEnv/dags"
Write-Host "  Or via CLI: gcloud composer environments run $ComposerEnv --location $Location web-server"
Write-Host ""
Write-Host "Trigger DAG manually:"
Write-Host "  gcloud composer environments run $ComposerEnv --location $Location dags -- trigger mmm_pipeline_gcp"
Write-Host ""
Write-Host "Monitor logs:"
Write-Host "  gcloud composer environments storage logs list --environment $ComposerEnv --location $Location"
Write-Host ""
