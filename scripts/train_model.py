"""Training wrapper used by Airflow DAG.
Loads processed data, trains MMM models and logs them to MLflow.
"""

import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.geo import analyze_geo_experiment
from models.mcmc import train_bayesian_mmm
from models.mmm_model import evaluate_temporal_holdout, get_revenue_col, prepare_model_data
from models.mlflow_tracking import MLflowTracker


DATA_PATH = ROOT / "data" / "processed" / "mmm_ready.csv"
CLEAN_DATA_PATH = ROOT / "data" / "processed" / "mmm_clean.csv"
ARTIFACTS_DIR = ROOT / "models" / "artifacts"
MLFLOW_DB = ROOT / "mlflow.db"
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT_NAME", "MMM-Orchestrated")
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{MLFLOW_DB.as_posix()}")
ENABLE_BAYESIAN = os.getenv("ENABLE_BAYESIAN_TRACKING", "1") != "0"
ENABLE_GEO = os.getenv("ENABLE_GEO_TRACKING", "1") != "0"
GEO_COLUMN = os.getenv("GEO_COLUMN")
GEO_TREATMENT_COLUMN = os.getenv("GEO_TREATMENT_COLUMN", "GEO_TREATMENT")
GEO_METRIC_COLUMN = os.getenv("GEO_METRIC_COLUMN")


def _sort_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if "DATE_DAY" in df.columns:
        df = df.copy()
        df["DATE_DAY"] = pd.to_datetime(df["DATE_DAY"], errors="coerce")
        df = df.sort_values("DATE_DAY")
    return df.reset_index(drop=True)


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, (np.floating, np.integer)):
        return float(value)
    return value


def _log_ridge_run(tracker: MLflowTracker, df: pd.DataFrame):
    print("Training Ridge MMM with temporal validation...")
    eval_info = evaluate_temporal_holdout(df)

    ridge_model = eval_info["model"]
    model_file = ARTIFACTS_DIR / "mmm_model.pkl"
    metrics_file = ARTIFACTS_DIR / "mmm_metrics.json"

    joblib.dump(ridge_model, model_file)

    ridge_metrics = {
        "train_r2": _safe_float(eval_info["train_r2"]),
        "train_mse": _safe_float(eval_info["train_mse"]),
        "train_mae": _safe_float(eval_info["train_mae"]),
        "test_r2": _safe_float(eval_info["test_r2"]),
        "test_mse": _safe_float(eval_info["test_mse"]),
        "test_mae": _safe_float(eval_info["test_mae"]),
        "test_mape": _safe_float(eval_info["test_mape"]),
        "target_col": eval_info["target_col"],
        "test_size": eval_info["test_size"],
    }

    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(ridge_metrics, f, indent=2, default=str)

    tracker.start_run("ridge-temporal", "ridge", tags={"validation": "temporal_holdout"})
    tracker.log_data_info(df, "training_data")
    tracker.log_params({"alpha": 1.0, "model_type": "ridge", "test_size": eval_info["test_size"]})
    tracker.log_metrics(
        {
            "train_r2": eval_info["train_r2"],
            "train_mse": eval_info["train_mse"],
            "train_mae": eval_info["train_mae"],
            "test_r2": eval_info["test_r2"],
            "test_mse": eval_info["test_mse"],
            "test_mae": eval_info["test_mae"],
            "test_mape": eval_info["test_mape"],
        }
    )
    tracker.log_model(ridge_model, "ridge-mmm")
    tracker.log_dict(
        {
            "split_idx": eval_info["split_idx"],
            "feature_cols": eval_info["feature_cols"],
            "model_file": str(model_file),
            "metrics_file": str(metrics_file),
        },
        "ridge_training.json",
    )
    tracker.end_run()

    print(f"Model saved to {model_file}")
    print(f"Metrics saved to {metrics_file}")


def _bayesian_holdout_metrics(df: pd.DataFrame, target_col: str):
    sorted_df = _sort_by_date(df)
    X, y, feature_cols = prepare_model_data(sorted_df, target_col=target_col)
    split_idx = max(int(len(sorted_df) * 0.8), 1)

    train_df = sorted_df.iloc[:split_idx]
    test_df = sorted_df.iloc[split_idx:]

    bayes_info = train_bayesian_mmm(train_df, target_col=target_col)

    if len(test_df) == 0:
        return bayes_info, {}

    feature_cols = bayes_info["feature_cols"]
    test_X = test_df[feature_cols].astype(float)
    test_scaled = bayes_info["scaler_X"].transform(test_X)
    y_scaled_pred = bayes_info["posterior_intercept"] + np.dot(test_scaled, bayes_info["posterior_beta"])
    y_pred = bayes_info["scaler_y"].inverse_transform(np.asarray(y_scaled_pred).reshape(-1, 1)).flatten()
    y_true = test_df[target_col].astype(float).values

    metrics = {
        "test_r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "test_mse": float(mean_squared_error(y_true, y_pred)) if len(y_true) > 0 else float("nan"),
        "test_mae": float(mean_absolute_error(y_true, y_pred)) if len(y_true) > 0 else float("nan"),
        "test_mape": float(np.nanmean(np.abs((y_true - y_pred) / np.where(y_true == 0, np.nan, y_true))) * 100)
        if len(y_true) > 0 else float("nan"),
        "split_idx": split_idx,
        "feature_count": len(feature_cols),
    }
    return bayes_info, metrics


def _log_bayesian_run(tracker: MLflowTracker, df: pd.DataFrame, target_col: str):
    print("Training Bayesian MMM and logging posterior summary...")
    bayes_info, metrics = _bayesian_holdout_metrics(df, target_col)

    tracker.start_run("bayesian-temporal", "bayesian", tags={"validation": "temporal_holdout"})
    tracker.log_data_info(df, "training_data")
    tracker.log_params(
        {
            "model_type": "bayesian",
            "feature_count": len(bayes_info["feature_cols"]),
        }
    )
    if metrics:
        tracker.log_metrics(metrics)
    tracker.log_dict(
        {
            "posterior_intercept": bayes_info["posterior_intercept"],
            "posterior_sigma": bayes_info["posterior_sigma"],
            "feature_cols": bayes_info["feature_cols"],
            "posterior_summary": bayes_info["posterior_summary"].reset_index().to_dict(orient="records"),
        },
        "bayesian_posterior.json",
    )
    tracker.end_run()

    print("Bayesian run logged")


def _log_geo_run(tracker: MLflowTracker):
    if not CLEAN_DATA_PATH.exists():
        print("Geo tracking skipped: cleaned dataset not found.")
        return

    df_geo = pd.read_csv(CLEAN_DATA_PATH)
    geo_column = GEO_COLUMN or ("ORGANISATION_PRIMARY_TERRITORY_NAME" if "ORGANISATION_PRIMARY_TERRITORY_NAME" in df_geo.columns else None)
    treatment_column = GEO_TREATMENT_COLUMN if GEO_TREATMENT_COLUMN in df_geo.columns else None
    metric_column = GEO_METRIC_COLUMN

    if geo_column is None or treatment_column is None:
        print("Geo tracking skipped: configure GEO_COLUMN and GEO_TREATMENT_COLUMN with real experiment labels.")
        return

    print("Analyzing geo experiment and logging MLflow run...")
    results = analyze_geo_experiment(
        df_geo,
        geo_column=geo_column,
        treatment_column=treatment_column,
        metric_column=metric_column,
    )

    summary = results["lift_summary"].copy()
    lift_series = pd.to_numeric(summary.get("lift_pct"), errors="coerce") if "lift_pct" in summary.columns else pd.Series(dtype=float)
    metrics = {
        "geo_segments": float(len(summary)),
        "avg_lift_pct": float(lift_series.fillna(0).mean()) if len(lift_series) > 0 else 0.0,
    }

    tracker.start_run("geo-experiment", "geo", tags={"analysis": "incrementality"})
    tracker.log_data_info(df_geo, "geo_data")
    tracker.log_metrics(metrics)
    tracker.log_dict(
        {
            "geo_column": geo_column,
            "treatment_column": treatment_column,
            "metric_column": results["metric_column"],
            "grouped": results["grouped"].to_dict(orient="records"),
            "lift_summary": results["lift_summary"].to_dict(orient="records"),
        },
        "geo_results.json",
    )
    tracker.end_run()
    print("Geo experiment run logged")


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_PATH.exists():
        raise SystemExit(f"Processed data not found: {DATA_PATH}. Run `python run_pipeline.py` first.")

    df = pd.read_csv(DATA_PATH)
    df = _sort_by_date(df)

    print("Training MMM models...")
    tracker = MLflowTracker(
        experiment_name=MLFLOW_EXPERIMENT,
        tracking_uri=TRACKING_URI,
    )

    _log_ridge_run(tracker, df)

    target_col = get_revenue_col(df)
    if ENABLE_BAYESIAN and target_col is not None:
        _log_bayesian_run(tracker, df, target_col)
    else:
        print("Bayesian tracking skipped.")

    if ENABLE_GEO:
        _log_geo_run(tracker)
    else:
        print("Geo tracking skipped.")

    print(f"\n✅ MLflow tracking complete. View with: mlflow ui --backend-store-uri {TRACKING_URI}")


if __name__ == "__main__":
    main()
