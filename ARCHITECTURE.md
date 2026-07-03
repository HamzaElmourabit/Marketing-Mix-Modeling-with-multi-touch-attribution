# 🏗️ ARCHITECTURE COMPLÈTE DU PROJET MMM

## Vue d'ensemble

Le projet **Marketing Mix Modeling (MMM)** est une solution end-to-end pour mesurer l'efficacité des canaux marketing, estimer les contributions et simuler des scénarios budgétaires.

## Orchestration Airflow

Airflow orchestre la chaîne MMM en production locale ou managée:

```text
Airflow DAG `mmm_pipeline`
    -> ETL + export BigQuery
    -> tests unitaires
    -> entraînement Ridge / Bayesian
    -> tracking MLflow
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MMM PROJECT ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [Raw Data]           [ETL Pipeline]         [Processed Data]       │
│  ├─ compressed_data   ├─ clean.py           ├─ mmm_ready.csv      │
│  │                    ├─ validation.py      ├─ mmm_clean.csv      │
│  │                    ├─ event_enrichment   └─ mmm_normalized.csv │
│  │                    ├─ feature_engineering│                      │
│  │                    ├─ normalize.py       │                      │
│  │                    └─ pipeline.py        │                      │
│  │                           │              │                      │
│  │                           └──────────────┤                      │
│  │                                          │                      │
│  └──────────────────────────┬───────────────┘                      │
│                             │                                       │
│                    ┌────────┴─────────┐                            │
│                    │                  │                            │
│               [BigQuery]    [Models & Dashboard]                   │
│               ├─ mmm table  ├─ mmm_model.py (Ridge)              │
│               │             ├─ dashboard/app.py (Streamlit)       │
│               │             └─ Dashboard pages:                    │
│               │                ├─ Dashboard (KPIs)                 │
│               │                ├─ Analyse Canaux                   │
│               │                ├─ Scénarios Budgétaires            │
│               │                ├─ Attribution                      │
│               │                ├─ Looker Embed                     │
│               │                └─ Configuration                    │
│               │                                                    │
│               └─────────────────────┬────────────────────────────┘ │
│                                     │                              │
│                           [Reports & Visualizations]              │
│                           ├─ PDF Report (LaTeX)                   │
│                           ├─ Assets/ (images)                     │
│                           └─ Looker Dashboards                    │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Structure de Répertoires

```
MMM_Project/
│
├── data/
│   ├── raw/
│   │   └── compressed_data.csv          # Source de données brutes
│   └── processed/
│       ├── mmm_ready.csv                # Données prêtes pour modélisation
│       ├── mmm_clean.csv                # Données nettoyées
│       └── mmm_normalized.csv           # Données normalisées
│
├── etl/
│   ├── config.py                        # Configuration, chemins, params
│   ├── validation.py                    # Règles qualité & validation
│   ├── clean.py                         # Nettoyage initial
│   ├── event_enrichment.py              # Features calendrier/événements
│   ├── feature_engineering.py           # Adstock, saturations, interactions
│   ├── normalize.py                     # Normalisation/standardisation
│   ├── pipeline.py                      # Orchestrateur ETL complet
│   └── load_bigquery.py                 # Export BigQuery
│
├── models/
│   └── mmm_model.py                     # Modèle Ridge (référence)
│
├── dashboard/
│   ├── app.py                           # Application Streamlit principale
│   ├── looker_integration.py            # Intégration Looker
│   └── pages/
│       └── looker_dashboards.py         # Page Looker Embed
│
├── bigquery/
│   ├── schema.sql                       # Schéma de la table MMM
│   └── queries.sql                      # Requêtes analytiques
│
├── looker/
│   └── lookml_models.py                 # Modèles LookML
│
├── scripts/
│   └── generate_report_assets.py        # Génération figures rapport
│
├── Assets/
│   ├── architecture_mmm.png             # Diagramme architecture
│   ├── Interface_dashboard.png          # Screenshot dashboard
│   ├── Attribution_multi_touch.png      # Attribution chart
│   ├── Budget_Scenarios_What_if.png     # Scénarios budgétaires
│   ├── ROI_Global.png                   # ROI global chart
│   ├── Top_5_canaux_les_plus_dépensiers.png
│   ├── Looker_dashboard.png             # Looker dashboard
│   └── Loading_Big_query.png            # BigQuery loading
│
├── run_pipeline.py                      # Point d'entrée pipeline
├── requirements.txt                     # Dépendances Python
├── .env.example                         # Template .env
├── MMM_Report.tex                       # Rapport LaTeX
├── README.md                            # Documentation principale
└── ARCHITECTURE.md                      # Ce fichier
```

---

## 🔄 Pipeline ETL (Flux de données)

### Étape 1 : Ingestion et Validation
- **Fichier** : `etl/config.py` + `etl/validation.py`
- **Entrée** : `data/raw/compressed_data.csv`
- **Règles** : Vérification types, nulls, ranges, cohérence métier
- **Sortie** : Validation report

### Étape 2 : Nettoyage
- **Fichier** : `etl/clean.py`
- **Actions** :
  - Normalisation des colonnes (trimming, lowercase)
  - Gestion des valeurs nulles (fill, drop, interpolation)
  - Conversion des types (datetime, numeric)
  - Standardisation des codes (verticales, régions)
- **Sortie** : `data/processed/mmm_clean.csv`

### Étape 3 : Enrichissement des Features
- **Fichier** : `etl/event_enrichment.py`
- **Features créées** :
  - Calendrier : jour de semaine, mois, saisonnalité (sin/cos)
  - Événements : jours fériés, périodes promotionnelles
  - Trends : tendance temporelle linéaire

### Étape 4 : Feature Engineering Marketing
- **Fichier** : `etl/feature_engineering.py`
- **Transformations clés** :
  - **Adstock** : effet retardé des dépenses (geometric adstock, decay rates)
  - **Saturation** : rendements décroissants (Hill equation)
  - **Lags** : décalages temporels (1-4 semaines)
  - **Interactions** : synergies entre canaux (Search × Display, etc.)

### Étape 5 : Normalisation
- **Fichier** : `etl/normalize.py`
- **Techniques** :
  - StandardScaler : centrage/réduction
  - MinMaxScaler : scaling 0-1
  - Log transforms : réduction asymétrie
- **Sortie** : `data/processed/mmm_normalized.csv`

### Étape 6 : Export
- **Fichier** : `etl/load_bigquery.py`
- **Cibles** :
  - CSV local : `data/processed/mmm_ready.csv`
  - BigQuery (optionnel) : table `MMM_dataset.mmm`

---

## 🤖 Modélisation (Approche Référence)

### Fichier Principal : `models/mmm_model.py`

#### Classe : `MMM_RidgeModel`
- **Algorithme** : Ridge Regression (scikit-learn)
- **Normalisation** : StandardScaler
- **Features** : Adstockées + Interactions + Controls (weekday, seasonality, trend)
- **Target** : Revenue (`FIRST_PURCHASES_ORIGINAL_PRICE`)

#### Méthodes Clés :
```python
train_mmm_model(df, target_col, alpha=1.0)
  → Entraîne le modèle, retourne coefficients & metrics (R2, MSE)

prepare_model_data(df, target_col)
  → Sélectionne features adstockées, valide target

estimate_budget_revenue(model_info, df, proposed_budget)
  → Simule impact d'un nouveau budget sur revenu

get_channel_attribution(model_info, df)
  → Calcule contribution relative par canal
```

#### Métriques :
- **R² Score** : % variance expliquée
- **MSE** : Erreur quadratique moyenne
- **Coefficients** : Poids relatifs des canaux
- **Elasticité** : Sensibilité budget (estimée par coefficient × avg feature)

---

## 📊 Dashboard Streamlit

### Fichier Principal : `dashboard/app.py`

#### Pages disponibles :

| Page | Fonction | Visualisations |
|------|----------|-----------------|
| 📊 **Dashboard** | KPIs & Tendances | Métriques, line charts, spend mix |
| 📈 **Analyse Canaux** | Performance par canal | Time series, ROI, spend comparison |
| 🎯 **Scénarios** | Simulations budgétaires | What-if analysis, slider controls |
| 🎨 **Attribution** | Multi-touch attribution | Pie chart, contribution bars |
| 🔗 **Looker** | Dashboards embarqués | Looker iframe (si configuré) |
| ⚙️ **Configuration** | Docs & diagnostics | Data health, documentation links |

#### Technologies Stack :
- **Framework** : Streamlit 1.28.1
- **Visualisation** : Plotly 5.18.0
- **Data** : Pandas 2.2.0, NumPy 1.26.3
- **ML** : scikit-learn 1.3.2
- **Attribution** : SHAP 0.44.1 (optional)

---

## 🔌 Intégration Looker

### Architecture Looker :
```
BigQuery (mmm table)
    ↓
LookML (model/views)
    ↓
Looker Dashboards
    ↓
Streamlit (embedded iframe)
```

### Fichiers :
- `looker/lookml_models.py` : Définitions LookML (views, measures, dimensions)
- `dashboard/looker_integration.py` : Génération tokens embed, iframe HTML
- `dashboard/pages/looker_dashboards.py` : UI pour sélection & affichage dashboards

---

## 🛠️ Technologies & Dépendances

### Data Processing
- **pandas** 2.2.0 : Manipulation DataFrames
- **numpy** 1.26.3 : Opérations numériques
- **tqdm** 4.67.0 : Progress bars

### Modélisation & ML
- **scikit-learn** 1.3.2 : Ridge regression, preprocessing
- **pymc** 5.10.0 : Modélisation Bayésienne (futur)
- **arviz** 0.17.1 : Diagnostics Bayésiens
- **pytensor** 2.18.6 : Tenseur computations

### Dashboard & Visualisation
- **streamlit** 1.28.1 : Framework web app
- **plotly** 5.18.0 : Graphiques interactifs
- **streamlit-plotly-events** 0.0.6 : Interactions Plotly

### Cloud & BigQuery
- **google-cloud-bigquery** 3.14.1 : Client BigQuery
- **google-cloud-bigquery-storage** 2.27.1 : Optimised transfers

### Attribution
- **shap** 0.44.1 : Shapley values pour attribution

### Utils & Config
- **python-dotenv** 1.0.0 : Variables d'environnement
- **pydantic** 2.5.0 : Data validation

### Testing & Qualité
- **pytest** 7.4.3 : Test framework
- **pytest-cov** 4.1.0 : Coverage reporting
- **black** 23.12.0 : Code formatting
- **flake8** 6.1.0 : Linting

---

## ⚡ Exécution du Projet

### 1. Installation
```bash
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec vos credentials (GCP, Looker, etc.)
```

### 2. Pipeline ETL
```bash
python run_pipeline.py
# Ou étapes individuelles :
python run_pipeline.py --validate-only
python run_pipeline.py --clean-only
python run_pipeline.py --bigquery  # + load to BigQuery
```

**Sortie** : `data/processed/mmm_ready.csv`

### 3. Dashboard Streamlit
```bash
streamlit run dashboard/app.py
# Accès : http://localhost:8501
```

### 4. Rapport LaTeX
```bash
pdflatex MMM_Report.tex
pdflatex MMM_Report.tex
# Génère MMM_Report.pdf (~30 pages, graphiques + images)
```

---

## 📈 Flux de Données Typique

```
User Input (ou fichier raw)
    ↓
[ETL Pipeline]
├─ clean.py         → data/processed/mmm_clean.csv
├─ event_enrich.py  → +event features
├─ feat_eng.py      → +adstock, saturation, interactions
├─ normalize.py     → data/processed/mmm_normalized.csv
└─ load_bigquery.py → BigQuery table
    ↓
[Models]
├─ train_mmm_model()        → Coefficients, R2, MSE
├─ estimate_budget_revenue() → Scénarios
└─ get_channel_attribution() → Contributions par canal
    ↓
[Dashboard Streamlit]
├─ Dashboard page      → Display KPIs
├─ Analyse Canaux      → Per-channel performance
├─ Scénarios           → What-if simulations
└─ Attribution         → Multi-touch breakdown
    ↓
[Reports]
├─ MMM_Report.pdf      → Rapport LaTeX complet
└─ Looker Dashboards   → Dashboards interactifs
```

---

## 🔐 Configuration (.env)

```bash
# GCP / BigQuery
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GCP_PROJECT_ID=my-project
BIGQUERY_DATASET_ID=MMM_dataset
BIGQUERY_TABLE_ID=mmm

# Paths
RAW_DATA_PATH=data/raw/compressed_data.csv
PROCESSED_DATA_PATH=data/processed/

# Looker (optional)
LOOKER_API_HOST=https://looker.company.com
LOOKER_API_KEY=your-key
LOOKER_API_SECRET=your-secret
LOOKER_DASHBOARD_IDS=mmm_overview,channel_performance
LOOKER_EMBED_USER_EMAIL=user@company.com
```

---

## 📊 Métriques Clés Calculées

### Dépenses (Spend)
- Total spend, spend par canal
- Spend trends (YoY, MoM)
- Spend mix (% par canal)

### Revenus (Revenue)
- Total revenue, revenue par verticale
- ROAS (Return on Ad Spend)
- Incremental revenue attribution

### Performance
- ROI par canal
- CPA (Cost Per Acquisition)
- ACOS (Advertising Cost of Sale)

### Modèle
- R² Score (model fit)
- Coefficients par canal (feature weights)
- Elasticité (sensibilité budget)
- Contribution absolue/relative

---

## 🚀 Roadmap & Futures Améliorations

### Modélisation Avancée
- [ ] Migration vers PyMC3/4 (modélisation Bayésienne complète)
- [ ] Adstock dynamique (variable decay par canal)
- [ ] Saturations complexes (multiple parameters)
- [ ] Interactions multi-way

### Cross-validation & Robustesse
- [ ] Time-series split validation
- [ ] Ensemble methods
- [ ] Sensitivity analysis

### Déploiement
- [ ] Containerisation Docker
- [ ] Deployment sur Cloud Run / App Engine
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Monitoring & alerting

### Attribution Avancée
- [ ] Shapley values multi-touch
- [ ] Last-click vs first-click
- [ ] Markov chains

---

## 📚 Documentation Additionnelle

- `README.md` : Vue d'ensemble générale
- `DATA_PIPELINE.md` : Détails ETL
- `DATA_IMPROVEMENTS.md` : Améliorations données
- `STREAMLIT_LOOKER.md` : Configuration Streamlit/Looker
- `MMM_VARIABLES_REFERENCE.md` : Dictionnaire des variables
- `QUICK_START_STREAMLIT.py` : Workflows courts

---

## ✅ Checklist Mise en Production

- [ ] Données brutes validées (`data/raw/compressed_data.csv`)
- [ ] Pipeline ETL exécutée : `python run_pipeline.py`
- [ ] Modèle MMM entraîné et validé
- [ ] Dashboard Streamlit testé localement
- [ ] BigQuery (optionnel) configuré & chargé
- [ ] Looker (optionnel) dashboards créés
- [ ] Rapport LaTeX généré : `pdflatex MMM_Report.tex`
- [ ] Variables d'environnement `.env` configurées
- [ ] Tests unitaires passent : `pytest`

---

**Dernière mise à jour** : Juin 2026  
**Responsable** : Équipe MMM  
**Version** : 1.0
