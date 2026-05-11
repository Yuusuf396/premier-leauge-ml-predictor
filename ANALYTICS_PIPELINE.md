# Data Quest — Analytics Pipeline
## Google Sheets Auto-Reporter + PySpark ML Pipeline

This repo integrates three layers:
- **Frontend**: React/Vite dashboard (existing)
- **API**: Django REST backend (existing)
- **ML**: scikit-learn pipeline + **PySpark at scale** + **automated reporting**

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node 20+
- Java 11 (for PySpark)

### Install Python dependencies
```bash
pip install -r requirements.txt
```

### Setup Java (if not installed)
```bash
# macOS
brew install openjdk@11
export JAVA_HOME=$(/usr/libexec/java_home -v 11)

# Ubuntu/WSL
sudo apt install openjdk-11-jdk
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

---

## Part 1: Google Sheets Auto-Reporter

**What it does**: Generates weekly model performance reports (accuracy, F1, matches scored) and auto-appends to a Google Sheet via scheduled GitHub Actions trigger.

### Setup (One-time)

#### 1. Create a Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project** → name it (e.g., `data-quest-reporter`)
3. **APIs & Services → Library**
4. Enable:
   - `Google Sheets API`
   - `Google Drive API`

#### 2. Create a Service Account
1. **APIs & Services → Credentials → Create Credentials → Service Account**
2. Name: `sheets-reporter` → click through → **Done**
3. Click the service account → **Keys tab → Add Key → JSON**
4. Save the JSON file somewhere safe (never commit to git)

#### 3. Share your Google Sheet
1. Create a new Google Sheet
2. Copy the ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```
3. Open the JSON key → find the `client_email` field
4. Share the Sheet with that email as **Editor**

#### 4. Test locally
```bash
export GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/your/key.json
export SPREADSHEET_ID=your_sheet_id

python automation/google_sheets_reporter.py
```

You should see:
```
── Google Sheets Auto-Reporter ──
  Generated 3 rows for W12-2026
✓ Appended 3 row(s) to 'Weekly Reports'.
✓ CSV saved locally: report_2026-03-17.csv
── Done ──
```

#### 5. Set up GitHub Actions
1. Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**
2. Add:
   - `GOOGLE_SERVICE_ACCOUNT_KEY` → paste entire JSON file contents
   - `SPREADSHEET_ID` → your Sheet ID
3. The workflow runs **every Monday at 8AM UTC** automatically
4. Trigger manually: **Actions tab → Weekly Sheets Report → Run workflow**

### Customizing Report Data

Edit the `generate_report()` function in `automation/google_sheets_reporter.py`:

```python
# Option 1: From your Django API
import requests
data = requests.get("https://your-api.com/api/model-runs/latest/").json()
df = pd.DataFrame(data)

# Option 2: From a CSV/Parquet file
df = pd.read_parquet("ml/outputs/latest_run.parquet")

# Option 3: From your database
import psycopg2
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
df = pd.read_sql("SELECT * FROM model_runs WHERE date >= now() - interval '7 days'", conn)
```

---

## Part 2: PySpark ML Pipeline

**What it does**: Reimplements the scikit-learn prediction system using PySpark — same temporal train/val/test splits, rolling form features, same models, but distributed & scalable.

### Run with synthetic data (no CSV needed)
```bash
python ml/pyspark_pipeline.py
```

Output:
```
── Data Quest | PySpark Pipeline ──
✓ Loaded 3,040 matches
  Train: 1,520  Val: 304  Test: 1,216

── Training LogisticRegression ──
  [LogisticRegression | Validation]  Accuracy=0.5921  F1=0.5634
  [LogisticRegression | Test]        Accuracy=0.5887  F1=0.5601

── Training RandomForest ──
  [RandomForest | Validation]        Accuracy=0.6134  F1=0.5977
  [RandomForest | Test]              Accuracy=0.6089  F1=0.5941

✓ Report saved → ml/outputs/predictions_report.csv
── Done ──
```

### Run with your real data
```bash
export DATA_PATH=/path/to/premier_league_2017_2026.csv
python ml/pyspark_pipeline.py
```

**Expected CSV columns:**
```
season, date, home_team, away_team,
home_goals, away_goals,
home_shots, away_shots, home_shots_on_target, away_shots_on_target,
home_corners, away_corners, home_fouls, away_fouls,
result  ← H / D / A
```

### Scaling to a distributed cluster

To run on AWS EMR or Databricks, just change the data path:

```python
# In ml/pyspark_pipeline.py
LOCAL_DATA_PATH = "s3://your-bucket/data/premier_league.csv"
```

Everything else stays the same — that's the power of Spark.

---

## Resume Bullets

Copy directly to your resume under **Data Quest** project:

```
Automated report delivery for Premier League model performance metrics, measured by
weekly accuracy and F1 deltas, by scripting the Google Drive API to generate and
append structured outputs on a scheduled GitHub Actions trigger.

Built a PySpark ETL and ML pipeline replicating the scikit-learn prediction system
at scale, using Spark Window functions for rolling form features and the Spark ML
Pipeline API with temporal train/val/test splits across 9 seasons (2017-2026).
```

Add **Apache Spark / PySpark** to your Skills section.

---

## Project Structure
```
data-quest/
├── api/                           ← Django REST backend
├── frontend/                      ← React/Vite/TS dashboard
├── ml/
│   ├── pipeline.py               ← Original scikit-learn pipeline
│   ├── pyspark_pipeline.py       ← NEW: PySpark version
│   ├── data/                     ← Match data (CSV/Parquet)
│   └── outputs/                  ← Model predictions & metrics
├── automation/
│   └── google_sheets_reporter.py ← NEW: Sheets auto-reporter
├── .github/
│   └── workflows/
│       └── weekly_report.yml     ← NEW: scheduled GitHub Actions
├── requirements.txt              ← Python dependencies
└── README.md
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `google.auth.exceptions.DefaultCredentialsError` | Verify `GOOGLE_SERVICE_ACCOUNT_KEY` env var points to JSON file |
| `403 The caller does not have permission` | Re-share the Sheet with service account email as **Editor** |
| `JAVA_HOME not set` | Install Java 11 and set `export JAVA_HOME=$(/usr/libexec/java_home)` |
| `AnalysisException: Path does not exist` | Set `DATA_PATH` env var or let the script generate synthetic data |
| GitHub Action fails with `KeyError: SPREADSHEET_ID` | Ensure both repo secrets are set under Settings → Secrets |
| `ModuleNotFoundError: No module named 'pyspark'` | Run `pip install -r requirements.txt` |

---

## Next Steps

- [ ] Connect the Sheets reporter to your Django API
- [ ] Add data quality checks to the Spark pipeline
- [ ] Deploy Spark pipeline to AWS EMR
- [ ] Add email notifications when model performance drops
- [ ] Set up a Streamlit dashboard pulling from the Google Sheet
