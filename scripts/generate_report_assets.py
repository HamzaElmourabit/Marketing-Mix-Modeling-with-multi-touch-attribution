"""Generates report assets (plots) for MMM_Report.tex
Runs on the repository, reads a sample of data/processed/mmm_ready.csv and writes images to Assets/
"""
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA_PATH = ROOT / 'data' / 'processed' / 'mmm_ready.csv'
ASSETS_DIR = ROOT / 'Assets'
ASSETS_DIR.mkdir(exist_ok=True)

def detect_date_col(df):
    date_cols = [c for c in df.columns if 'DATE' in c.upper()]
    return date_cols[0] if date_cols else None


def detect_revenue_col(df):
    candidates = ['FIRST_PURCHASES_ORIGINAL_PRICE', 'REVENUE', 'FIRST_PURCHASES']
    for token in candidates:
        for col in df.columns:
            if token in col.upper():
                return col
    return None


def detect_spend_cols(df):
    candidates = [c for c in df.columns if 'SPEND' in c.upper()]
    candidates = [c for c in candidates if 'INTERACTION' not in c.upper() and 'REVENUE_PER_SPEND' not in c.upper()]
    preferred = [c for c in candidates if not any(x in c.upper() for x in ['SCALED', 'LOG', 'LAG'])]
    if preferred:
        return preferred
    adstock = [c for c in candidates if 'ADSTOCK' in c.upper()]
    if adstock:
        return adstock
    return candidates


def load_sample(nrows=200000):
    if not DATA_PATH.exists():
        print(f"Data file not found: {DATA_PATH}")
        return None
    try:
        df = pd.read_csv(DATA_PATH, nrows=nrows)
    except Exception:
        # fallback to reading with low_memory
        df = pd.read_csv(DATA_PATH, nrows=nrows, low_memory=True)
    return df


def timeseries_plot(df, date_col, revenue_col, spend_cols):
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    ts = df.groupby(date_col).agg({revenue_col: 'sum', **{c: 'sum' for c in spend_cols}})
    ts['total_spend'] = ts[spend_cols].sum(axis=1)
    plt.figure(figsize=(12,6))
    plt.plot(ts.index, ts[revenue_col], label='Revenue', color='#2b83ba')
    plt.plot(ts.index, ts['total_spend'], label='Total Spend', color='#de2d26')
    plt.legend()
    plt.title('Revenue vs Total Spend over time')
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / 'timeseries_revenue_spend.png', dpi=150)
    plt.close()


def spend_by_channel(df, spend_cols):
    sums = df[spend_cols].sum().sort_values(ascending=False)
    plt.figure(figsize=(10,6))
    sns.barplot(x=sums.values, y=sums.index, palette='viridis')
    plt.title('Spend by Channel (sum)')
    plt.xlabel('Total Spend')
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / 'spend_by_channel.png', dpi=150)
    plt.close()


def corr_heatmap(df, spend_cols):
    use = [c for c in df.columns if c in spend_cols][:20]
    if len(use) < 2:
        return
    corr = df[use].corr()
    plt.figure(figsize=(10,8))
    sns.heatmap(corr, annot=False, cmap='coolwarm', center=0)
    plt.title('Correlation heatmap (top spend features)')
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / 'corr_heatmap.png', dpi=150)
    plt.close()


def model_and_coeffs(df):
    try:
        from models.mmm_model import train_mmm_model, get_channel_feature_cols
    except Exception as e:
        print('Could not import models.mmm_model:', e)
        return None

    try:
        model_info = train_mmm_model(df)
    except Exception as e:
        print('Model training failed:', e)
        return None

    coef = model_info['model'].named_steps['ridge'].coef_
    feature_cols = model_info['feature_cols']
    coeffs = pd.Series(coef, index=feature_cols).abs().sort_values(ascending=False)[:20]
    plt.figure(figsize=(10,6))
    sns.barplot(x=coeffs.values, y=coeffs.index, palette='magma')
    plt.title('Top absolute coefficients (Ridge)')
    plt.xlabel('Absolute coefficient')
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / 'model_coefficients.png', dpi=150)
    plt.close()

    # attribution pie
    contributions = []
    for name, weight in zip(feature_cols, coef):
        if 'ADSTOCK' in name or 'INTERACTION' in name:
            contributions.append((name, abs(weight) * float(model_info['feature_means'].get(name, 0.0))))
    if contributions:
        dfc = pd.DataFrame(contributions, columns=['channel','contrib']).sort_values('contrib', ascending=False).head(10)
        plt.figure(figsize=(7,7))
        plt.pie(dfc['contrib'], labels=dfc['channel'], autopct='%1.1f%%')
        plt.title('Attribution (top channels)')
        plt.tight_layout()
        plt.savefig(ASSETS_DIR / 'attribution_pie.png', dpi=150)
        plt.close()

    return model_info


def per_channel_plots(df, date_col, revenue_col, spend_cols):
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    channel_tex_lines = []
    for c in spend_cols:
        safe = c.replace(' ', '_').replace('/', '_').replace('%','pct')
        # timeseries spend
        try:
            ts = df.groupby(date_col)[c].sum()
            plt.figure(figsize=(10,3))
            plt.plot(ts.index, ts.values, color='#1f77b4')
            plt.title(f'Spend time series - {c}')
            plt.tight_layout()
            fname_spend = ASSETS_DIR / f'channel_{safe}_spend.png'
            plt.savefig(fname_spend, dpi=150)
            plt.close()
        except Exception:
            fname_spend = None

        # rolling ROI
        try:
            df_tmp = df[[date_col, c, revenue_col]].copy()
            df_tmp = df_tmp.dropna(subset=[date_col])
            df_tmp = df_tmp.sort_values(date_col)
            df_tmp['roi'] = df_tmp[revenue_col] / df_tmp[c].replace(0, np.nan)
            df_tmp['roi_roll'] = df_tmp['roi'].rolling(28, min_periods=1).mean()
            plt.figure(figsize=(10,3))
            plt.plot(df_tmp[date_col], df_tmp['roi_roll'], color='#2ca02c')
            plt.title(f'Rolling ROI ({c})')
            plt.tight_layout()
            fname_roi = ASSETS_DIR / f'channel_{safe}_roi.png'
            plt.savefig(fname_roi, dpi=150)
            plt.close()
        except Exception:
            fname_roi = None

        # stats
        try:
            total_spend = float(df[c].sum())
        except Exception:
            total_spend = 0.0
        try:
            avg_roi = float((df[revenue_col].sum()/df[c].sum()) if df[c].sum() else 0.0)
        except Exception:
            avg_roi = 0.0

        channel_tex_lines.append('\n\\clearpage\n')
        channel_tex_lines.append('\\section{Canal: %s}\n' % c.replace('_','\\_'))
        if fname_spend:
            channel_tex_lines.append('\\begin{figure}[H]\n  \\centering\n  \\includegraphics[width=0.95\\textwidth]{%s}\n  \\caption{Série temporelle des dépenses pour %s}\n\\end{figure}\n' % (fname_spend.name, c.replace('_','\\_')))
        if fname_roi:
            channel_tex_lines.append('\\begin{figure}[H]\n  \\centering\n  \\includegraphics[width=0.95\\textwidth]{%s}\n  \\caption{ROI rolling pour %s}\n\\end{figure}\n' % (fname_roi.name, c.replace('_','\\_')))

        channel_tex_lines.append('\\begin{table}[H]\n\\centering\n\\begin{tabular}{lr}\n\\toprule\\nMetric & Value\\\\\\n\\midrule\\nTotal spend & %0.2f\\\\\\nAverage ROI & %0.4f\\\\\\n\\bottomrule\\n\\end{tabular}\n\\caption{Stats sommaires pour %s}\n\\end{table}\n' % (total_spend, avg_roi, c.replace('_','\\_')))

    # write report_channels.tex
    rc_path = ROOT / 'report_channels.tex'
    with open(rc_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(channel_tex_lines))
    print('Wrote', rc_path)


def budget_scenarios(df, model_info, spend_cols):
    if model_info is None:
        return
    scenarios = []
    total_spend = df[spend_cols].sum().sum()
    top_spends = df[spend_cols].sum().sort_values(ascending=False)
    top_channels = list(top_spends.index[:3])
    base = {c: float(df[c].sum()) for c in spend_cols}
    # scenario 1: increase top channel by 20%
    s1 = base.copy()
    s1[top_channels[0]] = s1[top_channels[0]] * 1.2
    # scenario 2: move 10% budget from worst to best
    s2 = base.copy()
    worst = top_spends.index[-1]
    move = base[worst] * 0.1
    s2[worst] = s2[worst] - move
    s2[top_channels[0]] = s2[top_channels[0]] + move
    # scenario 3: equalize budget among top 3
    s3 = base.copy()
    top_total = sum(base[c] for c in top_channels)
    equal = top_total / 3
    for c in top_channels:
        s3[c] = equal
    scenarios = {'IncreaseTop': s1, 'Reallocate': s2, 'EqualizeTop3': s3}

    results = {}
    for name, bud in scenarios.items():
        try:
            pred = model_info and model_info and __estimate_budget_revenue_safe(model_info, df, bud)
        except Exception as e:
            pred = None
        results[name] = pred

    # plot results
    labels = list(results.keys())
    values = [results[k] if results[k] is not None else 0 for k in labels]
    plt.figure(figsize=(8,5))
    sns.barplot(x=labels, y=values, palette='pastel')
    plt.title('Projected revenue under scenarios')
    plt.ylabel('Projected revenue')
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / 'budget_scenarios.png', dpi=150)
    plt.close()


def __estimate_budget_revenue_safe(model_info, df, proposed_budget):
    try:
        from models.mmm_model import estimate_budget_revenue
        return estimate_budget_revenue(model_info, df, proposed_budget)
    except Exception:
        return None


def main():
    df = load_sample(nrows=100000)
    if df is None:
        print('No data loaded; exiting')
        return
    date_col = detect_date_col(df) or df.columns[0]
    revenue_col = detect_revenue_col(df) or df.columns[-1]
    spend_cols = detect_spend_cols(df)

    print('Detected date col:', date_col)
    print('Detected revenue col:', revenue_col)
    print('Detected spend cols count:', len(spend_cols))

    try:
        timeseries_plot(df, date_col, revenue_col, spend_cols)
    except Exception as e:
        print('timeseries_plot failed:', e)
    try:
        spend_by_channel(df, spend_cols)
    except Exception as e:
        print('spend_by_channel failed:', e)
    try:
        corr_heatmap(df, spend_cols)
    except Exception as e:
        print('corr_heatmap failed:', e)

    model_info = None
    try:
        model_info = model_and_coeffs(df)
    except Exception as e:
        print('model_and_coeffs failed:', e)

    try:
        budget_scenarios(df, model_info, spend_cols)
    except Exception as e:
        print('budget_scenarios failed:', e)

    # per-channel details and LaTeX snippet generation
    try:
        per_channel_plots(df, date_col, revenue_col, spend_cols)
    except Exception as e:
        print('per_channel_plots failed:', e)
    print('Assets generated in', ASSETS_DIR)


if __name__ == '__main__':
    main()
