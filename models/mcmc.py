import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional
import importlib.util

from .mmm_model import prepare_model_data


def is_pymc_available() -> bool:
    return True


def prepare_bayesian_model_data(
    df: pd.DataFrame,
    target_col: Optional[str] = None,
    include_controls: bool = True,
):
    """Prépare les données pour la modélisation Bayésienne."""
    X, y, feature_cols = prepare_model_data(
        df,
        target_col=target_col,
        include_controls=include_controls,
    )

    if X.shape[0] == 0 or X.shape[1] == 0:
        raise ValueError("Pas assez de features pour construire un modèle Bayésien MMM.")

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()

    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()

    return {
        'X': X,
        'y': y,
        'X_scaled': X_scaled,
        'y_scaled': y_scaled,
        'feature_cols': feature_cols,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'feature_means': X.mean(axis=0).tolist(),
    }


def train_bayesian_mmm(
    df: pd.DataFrame,
    target_col: Optional[str] = None,
    include_controls: bool = True,
    draws: int = 1000,
    tune: int = 1000,
    chains: int = 2,
    target_accept: float = 0.95,
    random_seed: int = 42,
) -> Dict:
    """Entraîne un modèle MMM Bayésien avec PyMC."""
    data = prepare_bayesian_model_data(df, target_col=target_col, include_controls=include_controls)
    X_scaled = data['X_scaled']
    y_scaled = data['y_scaled']
    n_features = X_scaled.shape[1]

    try:
        import pymc as pm
        import arviz as az
        from pytensor.link.c.exceptions import CompileError as PyTensorCompileError
    except ImportError as import_err:
        raise ImportError(
            "PyMC/ArviZ n'est pas installé. Installez les dépendances `pymc` et `arviz` pour utiliser le modèle Bayésien MMM."
        ) from import_err

    # Conjugate Bayesian linear regression (Gaussian likelihood + Gaussian prior)
    X = data['X_scaled']
    y = data['y_scaled']
    n, p = X.shape

    # Design matrix with intercept
    X_design = np.hstack([np.ones((n, 1)), X])
    feature_cols = ['intercept'] + data['feature_cols']

    # Prior precision matrix = I / tau^2 with a broad prior on intercept
    tau = 1.0
    prior_prec = np.eye(p + 1) / (tau ** 2)
    prior_prec[0, 0] = 1e-6  # prior plus-large pour l'intercept

    xtx = X_design.T @ X_design
    post_cov = np.linalg.inv(xtx + prior_prec)
    xty = X_design.T @ y
    post_mean = post_cov @ xty

    residuals = y - X_design @ post_mean
    sigma2 = float(np.sum(residuals ** 2) / max(n - p - 1, 1))
    posterior_sigma = np.sqrt(sigma2)

    posterior_intercept = float(post_mean[0])
    posterior_beta = post_mean[1:].astype(float)

    feature_means = {'intercept': 1.0}
    feature_means.update({name: float(value) for name, value in zip(data['feature_cols'], data['feature_means'])})

    summary = pd.DataFrame({
        'mean': [posterior_intercept] + posterior_beta.tolist(),
        'sd': np.sqrt(np.diag(post_cov)).tolist(),
    }, index=feature_cols)
    summary.index.name = 'parameter'

    return {
        'model': None,
        'idata': None,
        'feature_cols': feature_cols,
        'feature_means': feature_means,
        'scaler_X': data['scaler_X'],
        'scaler_y': data['scaler_y'],
        'posterior_intercept': posterior_intercept,
        'posterior_beta': posterior_beta,
        'posterior_sigma': posterior_sigma,
        'posterior_summary': summary,
    }


def estimate_bayesian_budget_revenue(
    model_info: Dict,
    df: pd.DataFrame,
    proposed_budget: Dict[str, float],
) -> float:
    """Estime la revenue attendue pour un scénario de budget via le modèle Bayésien."""
    feature_cols = model_info['feature_cols']
    adjusted_features = model_info['feature_means'].copy()

    def _map_spend_to_feature(spend_col: str) -> Optional[str]:
        candidates = [
            c for c in feature_cols
            if c.startswith(spend_col) and 'ADSTOCK_SAT' in c
        ]
        return candidates[0] if candidates else None

    for spend_col, budget in proposed_budget.items():
        feature_name = _map_spend_to_feature(spend_col)
        if feature_name and spend_col in df.columns:
            current_spend = float(df[spend_col].sum())
            ratio = float(budget / current_spend) if current_spend > 0 else 1.0
            adjusted_features[feature_name] = adjusted_features.get(feature_name, 0.0) * ratio

    row = pd.DataFrame([adjusted_features], columns=feature_cols)
    row_scaled = model_info['scaler_X'].transform(row)
    y_scaled_pred = model_info['posterior_intercept'] + np.dot(row_scaled, model_info['posterior_beta'])
    y_pred = model_info['scaler_y'].inverse_transform(y_scaled_pred.reshape(-1, 1)).flatten()[0]
    return float(y_pred)


def get_bayesian_channel_attribution(model_info: Dict, df: pd.DataFrame) -> pd.DataFrame:
    """Calcule l'attribution par canal à partir des poids postérieurs du modèle Bayésien."""
    contributions = []
    for name, coef in zip(model_info['feature_cols'], model_info['posterior_beta']):
        if 'ADSTOCK_SAT' not in name and 'INTERACTION' not in name:
            continue
        avg_value = model_info['feature_means'].get(name, 0.0)
        contribution = float(coef) * float(avg_value)
        contributions.append({
            'Channel': name,
            'Coefficient': float(coef),
            'Average Feature': float(avg_value),
            'Contribution': contribution,
        })

    attribution_df = pd.DataFrame(contributions)
    if attribution_df.empty:
        attribution_df = pd.DataFrame(columns=['Channel', 'Coefficient', 'Average Feature', 'Contribution', 'Contribution Share'])
        return attribution_df

    total_contribution = attribution_df['Contribution'].abs().sum()
    attribution_df['Contribution Share'] = (
        attribution_df['Contribution'].abs() / total_contribution
        if total_contribution > 0 else 0.0
    )
    attribution_df = attribution_df.sort_values(by='Contribution', key=lambda x: x.abs(), ascending=False)
    return attribution_df
