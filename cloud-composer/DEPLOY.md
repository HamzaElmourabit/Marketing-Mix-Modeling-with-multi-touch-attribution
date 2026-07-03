# Cloud Composer Deployment Guide

## Prérequis

1. **Compte GCP avec facturation activée**
   - Projet ID: `rh-etl-project-467521` (adapter si différent)

2. **CLI gcloud installée et configurée**
   ```bash
   gcloud auth login
   gcloud config set project rh-etl-project-467521
   ```

3. **APIs activées**
   ```bash
   gcloud services enable composer.googleapis.com
   gcloud services enable cloudscheduler.googleapis.com
   gcloud services enable bigquery.googleapis.com
   ```

4. **Compte de service pour Cloud Composer**
   ```bash
   gcloud iam service-accounts create cloud-composer-sa \
     --display-name="Cloud Composer Service Account"
   
   # Attribuer les rôles
   gcloud projects add-iam-policy-binding rh-etl-project-467521 \
     --member=serviceAccount:cloud-composer-sa@rh-etl-project-467521.iam.gserviceaccount.com \
     --role=roles/bigquery.dataEditor
   
   gcloud projects add-iam-policy-binding rh-etl-project-467521 \
     --member=serviceAccount:cloud-composer-sa@rh-etl-project-467521.iam.gserviceaccount.com \
     --role=roles/bigquery.jobUser
   
   gcloud projects add-iam-policy-binding rh-etl-project-467521 \
     --member=serviceAccount:cloud-composer-sa@rh-etl-project-467521.iam.gserviceaccount.com \
     --role=roles/storage.objectAdmin
   ```

## Déploiement Cloud Composer (méthode gcloud)

### Option 1 : Déploiement simple (environ 10-15 min)

```bash
gcloud composer environments create mmm-composer \
  --location europe-west1 \
  --python-version 3 \
  --machine-type n1-standard-4 \
  --node-count 3
```

### Option 2 : Déploiement avec configuration complète

```bash
gcloud composer environments create mmm-composer \
  --location europe-west1 \
  --python-version 3 \
  --machine-type n1-standard-4 \
  --node-count 3 \
  --env-variables \
    REPO_DIR=/home/airflow/gcs/data/mmm_repo,\
    GOOGLE_CLOUD_PROJECT=rh-etl-project-467521,\
    BIGQUERY_DATASET=MMM_datset,\
    BIGQUERY_TABLE=mmm \
  --service-account cloud-composer-sa@rh-etl-project-467521.iam.gserviceaccount.com
```

## Ajouter le DAG à Cloud Composer

### Méthode 1 : Copier le DAG via gsutil

```bash
# Obtenir le bucket GCS d'Airflow
COMPOSER_BUCKET=$(gcloud composer environments describe mmm-composer \
  --location europe-west1 \
  --format="value(config.dagGcsPrefix)" | sed 's/\/.*//')

# Copier le DAG
gsutil cp airflow/dags/mmm_pipeline.py gs://$COMPOSER_BUCKET/dags/

# Copier les requirements supplémentaires si nécessaire
gsutil cp requirements.txt gs://$COMPOSER_BUCKET/
```

### Méthode 2 : Déployer le repo complet

```bash
# Créer un archive du repo
tar -czf mmm_repo.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='.env' \
  --exclude='venv' \
  .

# Uploader le repo dans le bucket data/
gsutil cp mmm_repo.tar.gz gs://$COMPOSER_BUCKET/data/

# Dans Cloud Composer, extraire à l'init (via DAG custom ou startup script)
```

## Configurer les secrets BigQuery

### Option 1 : Service Account JSON via Secret Manager

```bash
# Créer une clé pour le compte de service
gcloud iam service-accounts keys create key.json \
  --iam-account=cloud-composer-sa@rh-etl-project-467521.iam.gserviceaccount.com

# Créer un secret GCP
gcloud secrets create mmm-bigquery-credentials \
  --replication-policy="automatic" \
  --data-file=key.json

# Attribuer l'accès au compte de service Composer
gcloud secrets add-iam-policy-binding mmm-bigquery-credentials \
  --member=serviceAccount:COMPOSER_SA_EMAIL \
  --role=roles/secretmanager.secretAccessor
```

Adapter votre DAG pour lire le secret :
```python
from airflow.providers.google.cloud.operators.secret_manager import GetSecretOperator

get_credentials = GetSecretOperator(
    task_id='get_credentials',
    secret_id='mmm-bigquery-credentials',
)
```

### Option 2 : Workload Identity (recommandé, automatique)

Cloud Composer utilise Workload Identity par défaut — le compte de service Composer accède à BigQuery sans clés JSON.

## Vérifier le déploiement

```bash
# Lister les environnements Composer
gcloud composer environments list --location europe-west1

# Décrire l'environnement
gcloud composer environments describe mmm-composer \
  --location europe-west1

# Accéder à l'UI Airflow
gcloud composer environments run mmm-composer \
  --location europe-west1 \
  web-server -- \
  airflow webserver

# Ou simplement ouvrir la UI via la console GCP
# Console > Cloud Composer > mmm-composer > Airflow webserver link
```

## Adapter le DAG pour Cloud Composer

Le DAG actuel utilise `BashOperator`. Pour Cloud Composer, vous pouvez :

1. **Option A (simple)** : Laisser le BashOperator mais copier le repo dans le bucket Composer
2. **Option B (robuste)** : Utiliser `PythonOperator` ou `KubernetesPodOperator`

Voir `airflow/dags/mmm_pipeline_gcp.py` pour une version adaptée à Cloud Composer.

## Coûts estimés

- **Cloud Composer instance** : ~$0.52/jour (n1-standard-4, 3 nœuds) = ~$15/mois
- **BigQuery** : dépend de l'usage (requêtes + stockage)
- **Cloud Storage** : ~$0.02/GB/mois pour petits datasets

## Troubleshooting

```bash
# Vérifier les logs de l'environnement
gcloud composer environments storage logs list \
  --environment mmm-composer \
  --location europe-west1

# Vérifier les tâches Airflow via CLI
gcloud composer environments run mmm-composer \
  --location europe-west1 \
  dags -- list

# Accéder au terminal du nœud scheduler
gcloud composer environments ssh mmm-composer \
  --location europe-west1
```

## Nettoyer (supprimer)

```bash
gcloud composer environments delete mmm-composer \
  --location europe-west1
```
