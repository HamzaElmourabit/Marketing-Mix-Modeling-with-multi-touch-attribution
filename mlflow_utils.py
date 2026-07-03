#!/usr/bin/env python
"""
MLflow Management Utility
Interface pour visualiser, comparer et gérer les modèles
"""

import argparse
import subprocess
import sys
from pathlib import Path
from models.mlflow_tracking import MLflowTracker
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parent
MLFLOW_DB = ROOT / "mlflow.db"


def start_ui(port: int = 5000):
    """Démarrer MLflow UI"""
    backend_uri = f"sqlite:///{MLFLOW_DB.as_posix()}"
    print(f"🚀 Starting MLflow UI on http://localhost:{port}")
    print(f"   Backend: {backend_uri}")
    
    cmd = [
        "mlflow", "ui",
        "--backend-store-uri", backend_uri,
        "--port", str(port)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n✋ MLflow UI stopped")
    except FileNotFoundError:
        print("❌ MLflow not installed. Run: pip install mlflow")
        sys.exit(1)


def list_experiments():
    """Lister les expériences"""
    tracker = MLflowTracker()
    
    import mlflow
    experiments = mlflow.search_experiments()
    
    if not experiments:
        print("No experiments found")
        return
    
    print("\n📊 Experiments:")
    print("-" * 60)
    for exp in experiments:
        print(f"  {exp.name:30} | ID: {exp.experiment_id:3} | Runs: {len(mlflow.search_runs(exp.experiment_id))}")


def compare_models(experiment_name: str):
    """Comparer les modèles d'une expérience"""
    comparison = MLflowTracker.compare_models(experiment_name)
    
    if comparison is None:
        print(f"❌ Experiment '{experiment_name}' not found")
        return
    
    if comparison.empty:
        print(f"No models found in {experiment_name}")
        return
    
    print(f"\n📈 Model Comparison - {experiment_name}")
    print("=" * 100)
    print(comparison.to_string(index=False))
    print("=" * 100)
    
    # Trouver le meilleur
    numeric_cols = comparison.select_dtypes(include=['float', 'int']).columns
    if len(numeric_cols) > 0:
        best_metric = numeric_cols[0]
        best_row = comparison.loc[comparison[best_metric].idxmax()]
        print(f"\n🏆 Best model: {best_row['run_name']} ({best_metric} = {best_row[best_metric]:.4f})")


def get_best_run(experiment_name: str, metric: str = "r2_score"):
    """Récupérer le meilleur run"""
    best_run = MLflowTracker.get_best_model(experiment_name, metric)
    
    if best_run is None:
        print(f"No models found in {experiment_name}")
        return
    
    print(f"\n🏆 Best Run - {experiment_name}")
    print(f"  Name: {best_run['tags.mlflow.runName']}")
    print(f"  Model: {best_run.get('tags.model_type', 'unknown')}")
    print(f"  {metric}: {best_run[f'metrics.{metric}']:.4f}")
    print(f"  Run ID: {best_run['run_id']}")


def train_and_track():
    """Entraîner et tracker automatiquement"""
    print("🏋️  Training model and tracking with MLflow...")
    
    from scripts.train_model import main as train_main
    train_main()
    
    print("\n✅ Training complete!")
    print(f"View results: mlflow ui --backend-store-uri sqlite:///{MLFLOW_DB.as_posix()}")


def cleanup_old_runs(experiment_name: str, keep_last_n: int = 5):
    """Nettoyer les anciens runs"""
    import mlflow
    
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"❌ Experiment '{experiment_name}' not found")
        return
    
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"]
    )
    
    if len(runs) <= keep_last_n:
        print(f"Only {len(runs)} runs. Nothing to clean.")
        return
    
    runs_to_delete = runs.iloc[keep_last_n:]
    
    for idx, run in runs_to_delete.iterrows():
        mlflow.delete_run(run['run_id'])
        print(f"Deleted: {run['tags.mlflow.runName']}")
    
    print(f"✅ Cleaned up {len(runs_to_delete)} old runs. Kept last {keep_last_n}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MLflow Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mlflow_utils.py ui              # Start MLflow UI
  python mlflow_utils.py list            # List all experiments
  python mlflow_utils.py compare ridge   # Compare Ridge models
  python mlflow_utils.py best ridge      # Get best Ridge model
  python mlflow_utils.py train           # Train and track
  python mlflow_utils.py cleanup ridge -k 5  # Keep last 5 runs
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # UI
    ui_parser = subparsers.add_parser("ui", help="Start MLflow UI")
    ui_parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    
    # List
    subparsers.add_parser("list", help="List experiments")
    
    # Compare
    compare_parser = subparsers.add_parser("compare", help="Compare models in experiment")
    compare_parser.add_argument("experiment", help="Experiment name")
    
    # Best
    best_parser = subparsers.add_parser("best", help="Get best model")
    best_parser.add_argument("experiment", help="Experiment name")
    best_parser.add_argument("-m", "--metric", default="r2_score", help="Metric to compare (default: r2_score)")
    
    # Train
    subparsers.add_parser("train", help="Train and track with MLflow")
    
    # Cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old runs")
    cleanup_parser.add_argument("experiment", help="Experiment name")
    cleanup_parser.add_argument("-k", "--keep", type=int, default=5, help="Keep last N runs (default: 5)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    if args.command == "ui":
        start_ui(args.port)
    elif args.command == "list":
        list_experiments()
    elif args.command == "compare":
        compare_models(args.experiment)
    elif args.command == "best":
        get_best_run(args.experiment, args.metric)
    elif args.command == "train":
        train_and_track()
    elif args.command == "cleanup":
        cleanup_old_runs(args.experiment, args.keep)
