import pandas as pd
from typing import Dict, Optional


def _find_revenue_column(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        'REVENUE',
        'FIRST_PURCHASES_ORIGINAL_PRICE',
        'FIRST_PURCHASES',
        'TOTAL_REVENUE',
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def analyze_geo_experiment(
    df: pd.DataFrame,
    geo_column: str = 'GEO_REGION',
    treatment_column: str = 'GEO_TREATMENT',
    metric_column: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """Analyse simple d'un test géo-expérimental."""
    if geo_column not in df.columns or treatment_column not in df.columns:
        raise ValueError(
            f"Colonnes requises manquantes pour l'analyse géo: {geo_column}, {treatment_column}"
        )

    metric_column = metric_column or _find_revenue_column(df)
    if metric_column is None:
        raise ValueError("Aucune colonne de métrique de revenu détectée pour l'analyse géo.")

    grouped = (
        df.groupby([geo_column, treatment_column])[metric_column]
        .agg(['sum', 'mean', 'count'])
        .reset_index()
    )

    uplift = grouped.pivot(index=geo_column, columns=treatment_column, values='mean')
    uplift = uplift.fillna(0.0)
    uplift['delta'] = None
    if set(['control', 'treatment']).issubset(uplift.columns):
        uplift['delta'] = uplift['treatment'] - uplift['control']
        uplift['lift_pct'] = uplift['delta'] / uplift['control'].replace({0: pd.NA})

    summary = pd.DataFrame(
        {
            'geo_segments': uplift.index,
            'control_mean': uplift.get('control', pd.Series(dtype=float)).values,
            'treatment_mean': uplift.get('treatment', pd.Series(dtype=float)).values,
            'delta': uplift.get('delta', pd.Series(dtype=float)).values,
            'lift_pct': uplift.get('lift_pct', pd.Series(dtype=float)).values,
        }
    )

    return {
        'metric_column': metric_column,
        'grouped': grouped,
        'lift_summary': summary,
    }
