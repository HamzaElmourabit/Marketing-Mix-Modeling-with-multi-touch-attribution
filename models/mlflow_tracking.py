"""
MLflow Tracking Module - Versioning et monitoring des modèles MMM
"""

import mlflow
import mlflow.sklearn
import mlflow.pyfunc
import pandas as pd
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional


class MLflowTracker:
    """Centralise le tracking des modèles MMM avec MLflow"""
    
    def __init__(self, experiment_name: str = "MMM-Pipeline", tracking_uri: str = None):
        """
        Args:
            experiment_name: Nom de l'expérience MLflow
            tracking_uri: URI de tracking MLflow. Par défaut, SQLite local.
        """
        self.experiment_name = experiment_name
        
        # Configurer MLflow sur SQLite local par défaut.
        root_dir = Path(__file__).resolve().parents[1]
        default_db_path = root_dir / "mlflow.db"

        if tracking_uri is None:
            tracking_uri = f"sqlite:///{default_db_path.as_posix()}"
        elif tracking_uri.startswith("sqlite:"):
            pass
        else:
            tracking_path = Path(tracking_uri).resolve()
            if tracking_path.is_dir() or tracking_path.suffix == "":
                tracking_uri = f"sqlite:///{default_db_path.as_posix()}"
            else:
                tracking_uri = f"sqlite:///{tracking_path.as_posix()}"

        mlflow.set_tracking_uri(tracking_uri)
        
        # Créer ou récupérer l'expérience active
        experiment = mlflow.set_experiment(experiment_name)
        self.experiment_id = experiment.experiment_id
    
    def start_run(self, run_name: str, model_type: str, tags: Optional[Dict] = None):
        """
        Démarrer un run MLflow
        
        Args:
            run_name: Nom du run (ex: "ridge_v1")
            model_type: Type (ridge, bayesian, geo)
            tags: Tags additionnels
        """
        mlflow.start_run(
            experiment_id=self.experiment_id,
            run_name=run_name,
            tags={
                "model_type": model_type,
                "framework": "python",
                **(tags or {})
            }
        )
    
    def log_metrics(self, metrics: Dict[str, float]):
        """Logger les métriques"""
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)
    
    def log_params(self, params: Dict[str, Any]):
        """Logger les paramètres"""
        for param_name, param_value in params.items():
            mlflow.log_param(param_name, str(param_value))
    
    def log_model(self, model, model_name: str, artifact_path: str = "models"):
        """Logger un modèle scikit-learn"""
        mlflow.sklearn.log_model(
            model,
            name=artifact_path,
            registered_model_name=model_name
        )
    
    def log_artifact_file(self, artifact_path: str):
        """Logger un fichier (JSON, CSV, etc.)"""
        mlflow.log_artifact(artifact_path)
    
    def log_dict(self, data: dict, filename: str = "metadata.json"):
        """Logger un dictionnaire comme artifact JSON"""
        with tempfile.NamedTemporaryFile("w", suffix=f"_{filename}", delete=False, encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2, default=str)
            json_path = tmp.name

        try:
            mlflow.log_artifact(json_path)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)
    
    def log_data_info(self, df: pd.DataFrame, name: str = "data_info"):
        """Logger info sur les données"""
        data_info = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "dtypes": str(df.dtypes),
            "null_count": df.isnull().sum().to_dict(),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2)
        }
        self.log_dict(data_info, f"{name}.json")
    
    def end_run(self, status: str = "FINISHED"):
        """Terminer le run"""
        mlflow.end_run(status=status)
    
    @staticmethod
    def get_best_model(experiment_name: str, metric: str = "r2_score"):
        """Récupérer le meilleur modèle d'une expérience"""
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return None
        
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=[f"metrics.{metric} DESC"],
            max_results=1
        )
        
        if len(runs) > 0:
            best_run = runs.iloc[0]
            return best_run
        return None
    
    @staticmethod
    def compare_models(experiment_name: str, metrics: list = None):
        """Comparer les modèles d'une expérience"""
        if metrics is None:
            metrics = ["r2_score", "mse", "mae"]
        
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            return None
        
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        
        comparison = []
        for _, run in runs.iterrows():
            row = {
                "run_id": run["run_id"],
                "run_name": run["tags.mlflow.runName"],
                "model_type": run.get("tags.model_type", "unknown"),
                "status": run["status"]
            }
            for metric in metrics:
                row[metric] = run.get(f"metrics.{metric}", None)
            comparison.append(row)
        
        return pd.DataFrame(comparison)


def track_ridge_model(df: pd.DataFrame, model, metrics: Dict, 
                     run_name: str = "ridge_baseline"):
    """Helper pour tracker un modèle Ridge"""
    tracker = MLflowTracker()
    tracker.start_run(run_name, "ridge")
    
    # Log données
    tracker.log_data_info(df, "training_data")
    
    # Log paramètres
    if hasattr(model, 'alpha'):
        tracker.log_params({"alpha": model.alpha})
    
    # Log métriques
    tracker.log_metrics(metrics)
    
    # Log modèle
    tracker.log_model(model, "ridge-mmm")
    
    tracker.end_run()


def track_bayesian_model(df: pd.DataFrame, posterior: Dict, metrics: Dict,
                        run_name: str = "bayesian_mmm"):
    """Helper pour tracker un modèle Bayesian"""
    tracker = MLflowTracker()
    tracker.start_run(run_name, "bayesian")
    
    # Log données
    tracker.log_data_info(df, "training_data")
    
    # Log métriques
    tracker.log_metrics(metrics)
    
    # Log posteriors comme JSON
    posterior_summary = {
        "beta_mean": posterior.get("beta_mean", []).tolist() if hasattr(posterior.get("beta_mean"), 'tolist') else posterior.get("beta_mean"),
        "beta_std": posterior.get("beta_std", []).tolist() if hasattr(posterior.get("beta_std"), 'tolist') else posterior.get("beta_std"),
        "intercept_mean": float(posterior.get("intercept_mean", 0)),
        "intercept_std": float(posterior.get("intercept_std", 0)),
    }
    tracker.log_dict(posterior_summary, "bayesian_posterior.json")
    
    tracker.end_run()


def track_geo_model(df: pd.DataFrame, results: Dict, metrics: Dict,
                   run_name: str = "geo_experiment"):
    """Helper pour tracker un modèle Geo"""
    tracker = MLflowTracker()
    tracker.start_run(run_name, "geo")
    
    # Log données
    tracker.log_data_info(df, "test_data")
    
    # Log métriques
    tracker.log_metrics(metrics)
    
    # Log résultats géo
    tracker.log_dict(results, "geo_results.json")
    
    tracker.end_run()


# Utilisation simple
if __name__ == "__main__":
    # Initialiser tracker
    tracker = MLflowTracker(experiment_name="MMM-Production")
    
    # Démarrer un run
    tracker.start_run("test_run", "ridge", tags={"env": "development"})
    
    # Logger données
    dummy_data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    tracker.log_data_info(dummy_data)
    
    # Logger métriques
    tracker.log_metrics({"r2_score": 0.92, "mse": 0.003})
    
    # Logger paramètres
    tracker.log_params({"alpha": 1.0, "max_iter": 1000})
    
    tracker.end_run()
    
    # Comparer modèles
    comparison = MLflowTracker.compare_models("MMM-Production")
    print(comparison)
