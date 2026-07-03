import pandas as pd
import numpy as np

from etl.normalize import normalize_dataset


def test_normalize_dataset_adds_scaled_and_log_columns():
    df = pd.DataFrame({
        'A': [1.0, 2.0, np.nan, 4.0],
        'B_SPEND': [0.0, 10.0, 20.0, 30.0],
        'C': [5.0, np.nan, 7.0, 8.0],
    })

    normalized_df, scalers = normalize_dataset(df)

    assert 'A_SCALED' in normalized_df.columns
    assert 'B_SPEND_LOG' in normalized_df.columns
    assert 'C_SCALED' in normalized_df.columns
    assert normalized_df.isnull().sum().sum() == 0
    assert isinstance(scalers, dict)
