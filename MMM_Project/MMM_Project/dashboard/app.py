"""
Streamlit App - MMM Pro Dashboard
Architecture multi-page avec Streamlit
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dashboard.pages.looker_dashboards import show_looker_page

# ===== CONFIG =====
st.set_page_config(
    page_title="MMM Pro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== STYLE NETFLIX =====
st.markdown("""
    <style>
        /* Dark theme */
        .main {
            background-color: #0e1117;
            color: #e6edf3;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #58a6ff;
            font-weight: 700;
        }
        
        /* Metrics */
        .stMetric {
            background-color: #1a1c24;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #58a6ff;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #238636;
            color: white;
            border-radius: 5px;
            padding: 10px 20px;
            font-weight: 600;
        }
        
        .stButton > button:hover {
            background-color: #2ea043;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            color: #58a6ff;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background-color: #1a1c24;
        }
    </style>
""", unsafe_allow_html=True)

# ===== SETUP PATHS =====
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MMDATA_PATH = DATA_DIR / "mmm_ready.csv"

# ===== CACHE DATA LOADING =====
@st.cache_data
def load_mmm_data():
    """Cache le chargement des données"""
    if not MMDATA_PATH.exists():
        return None
    
    df = pd.read_csv(MMDATA_PATH)
    
    # Parse dates
    date_cols = [col for col in df.columns if 'DATE' in col.upper()]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df

# ===== MAIN APP =====
def main():
    st.sidebar.title("🎯 Navigation")
    
    # Menu principal
    page = st.sidebar.radio(
        "Sélectionnez une page",
        ["📊 Dashboard", "📈 Analyse Canaux", "🎯 Scenarios", "🎨 Attribution", "🔗 Looker", "⚙️ Configuration"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        "💡 **MMM Pro Dashboard**\n"
        "Marketing Mix Modeling avec PyMC3\n"
        "Attribution multi-touch et scenarios budgétaires"
    )
    
    # Charger les données
    df = load_mmm_data()
    
    if df is None:
        st.error("❌ Données MMM non trouvées. Lancez d'abord la pipeline ETL.")
        st.code("python run_pipeline.py")
        return
    
    # Router vers les pages
    if page == "📊 Dashboard":
        show_dashboard(df)
    elif page == "📈 Analyse Canaux":
        show_channel_analysis(df)
    elif page == "🎯 Scenarios":
        show_scenarios(df)
    elif page == "🎨 Attribution":
        show_attribution(df)
    elif page == "🔗 Looker":
        show_looker_page()
    elif page == "⚙️ Configuration":
        show_config()


def show_dashboard(df):
    """Page principale - KPIs et trends"""
    st.markdown("# 📊 Dashboard MMM")
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        date_col = [c for c in df.columns if 'DATE' in c.upper()][0]
        start_date = st.date_input("Date début", value=df[date_col].min().date())
    with col2:
        end_date = st.date_input("Date fin", value=df[date_col].max().date())
    
    # Filter data
    df_filtered = df[
        (df[date_col].dt.date >= start_date) & 
        (df[date_col].dt.date <= end_date)
    ].copy()
    
    # ===== KPI SECTION =====
    st.markdown("## 🔥 Key Metrics")
    
    # Identifier les colonnes
    spend_cols = [c for c in df_filtered.columns if 'SPEND' in c.upper() and 'ADSTOCK' not in c and 'LAG' not in c]
    revenue_col = next((c for c in df_filtered.columns if 'FIRST_PURCHASES_ORIGINAL_PRICE' in c or 'REVENUE' in c.upper()), None)
    
    total_spend = df_filtered[spend_cols].sum().sum() if spend_cols else 0
    total_revenue = df_filtered[revenue_col].sum() if revenue_col else 0
    roi = total_revenue / total_spend if total_spend > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Total Spend",
            f"${total_spend:,.0f}",
            delta=f"{(total_spend/len(df_filtered)):,.0f} /day" if len(df_filtered) > 0 else None
        )
    
    with col2:
        st.metric(
            "📈 Total Revenue",
            f"${total_revenue:,.0f}",
            delta=f"{(total_revenue/len(df_filtered)):,.0f} /day" if len(df_filtered) > 0 else None
        )
    
    with col3:
        st.metric(
            "🎯 ROI",
            f"{roi:.2f}x",
            delta=f"Revenue per $ spent"
        )
    
    with col4:
        days = len(df_filtered)
        st.metric(
            "📅 Période",
            f"{days} days",
            delta=f"{(total_spend/days):,.0f} spend/day" if days > 0 else None
        )
    
    # ===== TRENDS =====
    st.markdown("## 📊 Trends")
    
    tab1, tab2, tab3 = st.tabs(["Revenue Trend", "Spend Trend", "ROI Trend"])
    
    with tab1:
        date_col_name = date_col
        revenue_ts = df_filtered.groupby(date_col_name)[revenue_col].sum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=revenue_ts.index,
            y=revenue_ts.values,
            mode='lines',
            name='Revenue',
            line=dict(color='#58a6ff', width=3),
            fill='tozeroy'
        ))
        fig.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            title='Daily Revenue'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        spend_ts = df_filtered.groupby(date_col_name)[spend_cols].sum().sum(axis=1)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=spend_ts.index,
            y=spend_ts.values,
            mode='lines',
            name='Spend',
            line=dict(color='#f85149', width=3),
            fill='tozeroy'
        ))
        fig.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            title='Daily Spend'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        roi_ts = (df_filtered.groupby(date_col_name)[revenue_col].sum() / 
                 df_filtered.groupby(date_col_name)[spend_cols].sum().sum(axis=1))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=roi_ts.index,
            y=roi_ts.values,
            mode='lines+markers',
            name='ROI',
            line=dict(color='#79c0ff', width=3)
        ))
        fig.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            title='Daily ROI'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # ===== CHANNEL MIX =====
    st.markdown("## 💰 Channel Spend Mix")
    
    channel_spend = df_filtered[spend_cols].sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=channel_spend.index,
        values=channel_spend.values,
        hole=.3
    )])
    fig.update_layout(template='plotly_dark', title='Spend Distribution')
    st.plotly_chart(fig, use_container_width=True)


def show_channel_analysis(df):
    """Analyse détaillée par canal"""
    st.markdown("# 📈 Analyse par Canal")
    
    spend_cols = [c for c in df.columns if 'SPEND' in c.upper() and 'ADSTOCK' not in c and 'LAG' not in c]
    revenue_col = next((c for c in df.columns if 'FIRST_PURCHASES_ORIGINAL_PRICE' in c or 'REVENUE' in c.upper()), None)
    
    # Sélection canal
    selected_channel = st.selectbox("Sélectionnez un canal", spend_cols)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            f"Total {selected_channel}",
            f"${df[selected_channel].sum():,.0f}"
        )
    
    with col2:
        roi_channel = df[revenue_col].sum() / df[selected_channel].sum() if df[selected_channel].sum() > 0 else 0
        st.metric(
            f"ROI {selected_channel}",
            f"{roi_channel:.2f}x"
        )
    
    # Scatter: Spend vs Revenue
    date_col = [c for c in df.columns if 'DATE' in c.upper()][0]
    df_daily = df.groupby(date_col).agg({
        selected_channel: 'sum',
        revenue_col: 'sum'
    }).reset_index()
    
    fig = px.scatter(
        df_daily,
        x=selected_channel,
        y=revenue_col,
        trendline='ols',
        title=f'{selected_channel} vs Revenue'
    )
    fig.update_layout(template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)


def show_scenarios(df):
    """What-if scenarios budgétaires"""
    st.markdown("# 🎯 Budget Scenarios (What-If Analysis)")
    
    st.info(
        "💡 Simulez différents allocations budgétaires et voyez l'impact prédit sur le ROI\n"
        "⚠️ Nécessite un modèle MMM entraîné (PyMC3)"
    )
    
    spend_cols = [c for c in df.columns if 'SPEND' in c.upper() and 'ADSTOCK' not in c and 'LAG' not in c]
    revenue_col = next((c for c in df.columns if 'FIRST_PURCHASES_ORIGINAL_PRICE' in c or 'REVENUE' in c.upper()), None)
    
    # Budget actuel
    current_budget = df[spend_cols].sum().sum()
    
    st.markdown("## 💰 Budget Actuel")
    st.metric("Total Budget", f"${current_budget:,.0f}")
    
    # Sliders pour ajuster le budget par canal
    st.markdown("## 🎚️ Ajustez l'allocation budgétaire")
    
    allocation_pct = {}
    cols = st.columns(len(spend_cols))
    
    for idx, (col_name, col) in enumerate(zip(spend_cols, cols)):
        current_pct = (df[col_name].sum() / current_budget) * 100
        with col:
            allocation_pct[col_name] = st.slider(
                f"{col_name.replace('_SPEND', '')}",
                min_value=0,
                max_value=100,
                value=int(current_pct),
                step=5
            )
    
    # Vérifier que la somme = 100%
    total_pct = sum(allocation_pct.values())
    
    if abs(total_pct - 100) > 1:
        st.warning(f"⚠️ Total = {total_pct}%. Doit être 100%")
    else:
        st.success("✅ Allocation valide")
        
        # Calculer le budget proposé
        st.markdown("## 📊 Budget Proposé")
        
        proposed_budget = {}
        for channel, pct in allocation_pct.items():
            proposed_budget[channel] = (current_budget * pct) / 100
        
        proposed_df = pd.DataFrame({
            'Channel': list(proposed_budget.keys()),
            'Current': [df[c].sum() for c in proposed_budget.keys()],
            'Proposed': list(proposed_budget.values()),
            'Change': [proposed_budget[c] - df[c].sum() for c in proposed_budget.keys()]
        })
        
        proposed_df['Change %'] = (proposed_df['Change'] / proposed_df['Current'] * 100).round(1)
        
        st.dataframe(proposed_df, use_container_width=True)


def show_attribution(df):
    """Attribution multi-touch (Shapley)"""
    st.markdown("# 🎨 Attribution Multi-Touch")
    
    st.info(
        "💡 Attribution via Shapley Values\n"
        "Attribue le crédit à chaque canal de manière équitable"
    )
    
    spend_cols = [c for c in df.columns if 'SPEND' in c.upper() and 'ADSTOCK' not in c and 'LAG' not in c]
    revenue_col = next((c for c in df.columns if 'FIRST_PURCHASES_ORIGINAL_PRICE' in c or 'REVENUE' in c.upper()), None)
    
    st.markdown("## 📊 Attribution Model")
    
    attribution_model = st.radio(
        "Modèle d'attribution",
        ["First Touch", "Last Touch", "Linear", "Time Decay", "Shapley Value (Advanced)"]
    )
    
    # Simulation d'attribution (dépend du modèle entraîné)
    if attribution_model == "Linear":
        # Attribution linéaire: crédit égal
        channel_contrib = {}
        total_revenue = df[revenue_col].sum()
        for channel in spend_cols:
            channel_contrib[channel] = total_revenue / len(spend_cols)
    
    elif attribution_model == "First Touch":
        # Premier canal = tout le crédit (simulation)
        channel_contrib = {spend_cols[0]: df[revenue_col].sum()}
        for channel in spend_cols[1:]:
            channel_contrib[channel] = 0
    
    else:
        # Default: linear
        channel_contrib = {}
        total_revenue = df[revenue_col].sum()
        for channel in spend_cols:
            channel_contrib[channel] = total_revenue / len(spend_cols)
    
    # Visualiser
    attribution_df = pd.DataFrame({
        'Channel': list(channel_contrib.keys()),
        'Attributed Revenue': list(channel_contrib.values())
    })
    
    fig = px.bar(
        attribution_df,
        x='Channel',
        y='Attributed Revenue',
        title=f'Revenue Attribution - {attribution_model}'
    )
    fig.update_layout(template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)


def show_config():
    """Configuration et docs"""
    st.markdown("# ⚙️ Configuration")
    
    tab1, tab2, tab3 = st.tabs(["📊 Data Status", "🔧 MMM Config", "📚 Documentation"])
    
    with tab1:
        st.markdown("## Data Files")
        
        if MMDATA_PATH.exists():
            df = load_mmm_data()
            st.success(f"✅ mmm_ready.csv loaded")
            st.metric("Rows", len(df))
            st.metric("Columns", len(df.columns))
            
            st.markdown("### Column Info")
            col_info = pd.DataFrame({
                'Column': df.columns,
                'Type': [str(df[col].dtype) for col in df.columns],
                'Non-Null': [df[col].notna().sum() for col in df.columns]
            })
            st.dataframe(col_info, use_container_width=True)
        else:
            st.error(f"❌ mmm_ready.csv not found at {MMDATA_PATH}")
    
    with tab2:
        st.markdown("## Channel Configuration")
        
        config_info = {
            'Channel': [
                'Google Search', 'Google Shopping', 'Google Display',
                'Google PMax', 'Google Video', 'Meta Facebook',
                'Meta Instagram', 'TikTok'
            ],
            'Decay': [0.5, 0.4, 0.7, 0.6, 0.65, 0.6, 0.65, 0.7],
            'Saturation': [1.5, 1.5, 1.2, 1.5, 1.3, 1.4, 1.3, 1.2]
        }
        
        config_df = pd.DataFrame(config_info)
        st.dataframe(config_df, use_container_width=True)
    
    with tab3:
        st.markdown("## Documentation")
        
        st.markdown("""
        ### 📖 Guides Disponibles
        
        - **DATA_PIPELINE.md** - Pipeline ETL complète
        - **DATA_IMPROVEMENTS.md** - Améliorations apportées
        - **MMM_VARIABLES_REFERENCE.md** - Référence des variables
        
        ### 🚀 Quick Start
        
        ```bash
        # Lancer la pipeline Data
        python run_pipeline.py
        
        # Lancer le dashboard
        streamlit run dashboard/app.py
        ```
        
        ### 📞 Support
        
        Pour des questions sur la modélisation MMM, consultez la documentation dans le dossier racine.
        """)


if __name__ == "__main__":
    main()