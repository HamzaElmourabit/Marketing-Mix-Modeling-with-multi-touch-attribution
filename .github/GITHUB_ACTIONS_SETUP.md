# GitHub Actions - Orchestration Gratuite

## Setup (5 minutes)

### 1. Initialiser le repo Git

```powershell
cd c:\Users\khadi\MMM_Project\MMM_Project

# Initialiser git
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Ajouter tous les fichiers
git add .

# Commit initial
git commit -m "Initial commit: MMM pipeline with Airflow and GitHub Actions"
```

### 2. Créer un repo sur GitHub

- Allez sur https://github.com/new
- Nommez-le `mmm-project`
- Ne cochez PAS "Initialize with README" (on l'a déjà)
- Cliquez "Create repository"

### 3. Pousser le code

Remplacez `YOUR_USERNAME` par votre pseudo GitHub :

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mmm-project.git
git push -u origin main
```

### 4. Vérifier le workflow

- Allez sur https://github.com/YOUR_USERNAME/mmm-project/actions
- Le workflow `MMM Pipeline Orchestration` devrait apparaître
- Cliquez sur "Run workflow" pour déclencher la première exécution

---

## Fonctionnement

### ⏱️ Calendrier

Le pipeline s'exécute **chaque jour à 2h du matin UTC** (3h en été) :

```yaml
schedule:
  - cron: '0 2 * * *'
```

Pour changer l'heure, modifiez `.github/workflows/mmm-orchestration.yml` :
- `0` = minute
- `2` = heure (0-23)
- `*` = jour du mois
- `*` = mois
- `*` = jour de la semaine

Exemples :
- `0 0 * * *` → minuit UTC
- `0 12 * * *` → midi UTC
- `0 2 * * MON` → lundi 2h UTC (exécution hebdomadaire)

### 🔐 Ajouter les secrets BigQuery

Si vous voulez que le workflow charge les données vers BigQuery :

1. Allez sur https://github.com/YOUR_USERNAME/mmm-project/settings/secrets/actions
2. Cliquez "New repository secret"
3. Nommez-le `GCP_CREDENTIALS`
4. Collez le contenu de votre fichier `service-account.json`

Puis, décommentez les lignes dans le workflow :

```yaml
env:
  GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_CREDENTIALS }}
```

### 📊 Vérifier les exécutions

**Dans GitHub** :
- Allez sur l'onglet **Actions**
- Cliquez sur la dernière exécution
- Voir les logs de chaque étape

**Artefacts** (modèles, logs) :
- En bas de chaque run, cliquez sur "Artifacts"
- Téléchargez `mmm-artifacts` et `pipeline-logs`

---

## Quotas gratuits

✅ **2000 minutes/mois** (ubuntu-latest)
✅ **Votre usage : ~2-3 min/jour = ~60-90 min/mois**
✅ **Marge confortable**

---

## Troubleshooting

### ❌ Workflow échoue

1. Cliquez sur la run échouée
2. Déroulez l'étape qui a échoué
3. Vérifiez les logs d'erreur
4. Les erreurs couantes :
   - `ModuleNotFoundError` → ajouter le package à `requirements.txt`
   - `FileNotFoundError: data/processed/mmm_ready.csv` → vérifier que `run_pipeline.py` génère bien le fichier
   - `PermissionError` → vérifier les droits sur les fichiers

### ❓ Comment modifier le schedule ?

Éditez `.github/workflows/mmm-orchestration.yml` → section `schedule` → `cron`

### ❓ Comment déclencher manuellement ?

```
GitHub > Actions > MMM Pipeline Orchestration > Run workflow
```

---

## Comparaison : Airflow local vs GitHub Actions

| Aspect | Airflow local | GitHub Actions |
|--------|---------------|---|
| **Coût** | 0€ | 0€ |
| **Setup** | Docker (déjà fait) | Git + GitHub (5 min) |
| **Interface** | Web UI locale | GitHub UI |
| **Portabilité** | Que sur votre machine | Accessible partout |
| **Storag des logs** | Local | GitHub (90 jours) |
| **Meileur pour** | Développement / Debug | Production légère |

---

## Prochaines étapes

1. ✅ Push le code sur GitHub
2. ✅ Vérifier que le workflow s'exécute
3. ✅ (Optionnel) Ajouter les secrets BigQuery
4. ✅ Garder Airflow local pour les tests/développement
