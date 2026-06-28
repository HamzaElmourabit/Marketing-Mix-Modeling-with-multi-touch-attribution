Airflow quick start for this repository

1) Prérequis
- Docker & Docker Compose installés
- Port libre pour Airflow (ex: 8080)

2) Démarrer Airflow (méthode officielle rapide)

```bash
# depuis la racine du repo
git clone https://github.com/apache/airflow.git /tmp/airflow-src  # si vous voulez les exemples
cd <repo-root>
# Créez un utilisateur et démarrez via la composition officielle d'Airflow (ou installez localement)
# Voir https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html
docker compose up -d
```

3) Déployer le DAG
- Copier ce repo dans le dossier où Airflow lit les `dags/` (par défaut `/opt/airflow/dags`).
- Le DAG `mmm_pipeline` se trouve dans `airflow/dags/mmm_pipeline.py`.

4) Notes d'exécution
- Le DAG appelle `python run_pipeline.py --bigquery` et `python scripts/train_model.py`.
- Assurez-vous que l'image Airflow exécute les commandes depuis la racine du projet (ou ajustez `bash_command` dans le DAG pour `cd` dans le repo).

5) Permissions et secrets
- Pour charger vers BigQuery, configurez `GOOGLE_APPLICATION_CREDENTIALS` ou utilisez Workload Identity/Secret Manager.
