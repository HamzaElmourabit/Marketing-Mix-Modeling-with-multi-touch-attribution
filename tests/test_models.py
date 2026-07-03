import pandas as pd
import numpy as np

from models.mmm_model import prepare_model_data, train_mmm_model
from models.mcmc import train_bayesian_mmm, estimate_bayesian_budget_revenue


def make_sample_mmm_df():
    return pd.DataFrame({
        'FIRST_PURCHASES_ORIGINAL_PRICE': [100, 120, 130, 150, 160],
        'GOOGLE_PAID_SEARCH_SPEND_ADSTOCK_SAT': [10, 12, 11, 15, 14],
        'GOOGLE_DISPLAY_SPEND_ADSTOCK_SAT': [5, 6, 7, 8, 7],
        'META_FACEBOOK_SPEND_ADSTOCK_SAT': [8, 9, 8, 10, 9],
        'SEARCH_DISPLAY_INTERACTION': [50, 72, 77, 120, 98],
        'WEEKDAY': [1, 2, 3, 4, 5],
        'MONTH_SIN': np.sin([0, 1, 2, 3, 4]),
        'MONTH_COS': np.cos([0, 1, 2, 3, 4]),
        'TREND': [1, 2, 3, 4, 5],
    })


def test_prepare_model_data_returns_expected_shapes():
    df = make_sample_mmm_df()
    X, y, feature_cols = prepare_model_data(df)

    assert X.shape[0] == len(df)
    assert y.shape[0] == len(df)
    assert len(feature_cols) >= 3
    assert 'FIRST_PURCHASES_ORIGINAL_PRICE' not in feature_cols
    assert 'WEEKDAY' in feature_cols


def test_train_mmm_model_computes_metrics():
    df = make_sample_mmm_df()
    model_info = train_mmm_model(df)

    assert model_info['r2'] >= 0.0
    assert model_info['mse'] >= 0.0
    assert isinstance(model_info['feature_cols'], list)
    assert len(model_info['y_pred']) == len(df)


def test_train_bayesian_mmm_returns_posterior():
    df = make_sample_mmm_df()
    model_info = train_bayesian_mmm(df)

    assert 'posterior_intercept' in model_info
    assert 'posterior_beta' in model_info
    assert len(model_info['posterior_beta']) == len(model_info['feature_cols'])
    assert model_info['posterior_sigma'] > 0


def test_estimate_bayesian_budget_revenue_changes_with_budget():
    df = make_sample_mmm_df()
    model_info = train_bayesian_mmm(df)

    current = estimate_bayesian_budget_revenue(
        model_info,
        df,
        {'GOOGLE_PAID_SEARCH_SPEND': df['GOOGLE_PAID_SEARCH_SPEND_ADSTOCK_SAT'].sum()}
    )
    proposed = estimate_bayesian_budget_revenue(
        model_info,
        df,
        {'GOOGLE_PAID_SEARCH_SPEND': df['GOOGLE_PAID_SEARCH_SPEND_ADSTOCK_SAT'].sum() * 1.2}
    )

    assert isinstance(current, float)
    assert isinstance(proposed, float)
    assert proposed != current
