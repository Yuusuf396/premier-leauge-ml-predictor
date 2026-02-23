# Premier League match prediction — Plan

## Goal
Build a reproducible machine-learning pipeline that predicts Premier League match outcomes (and/or scores) using historical match data and engineered “past-only” features.

---

## Step 1 — Collect & validate data (2016–2025)
- Gather historical match data (e.g., `E0.csv` seasons 2016–2025).
- Standardize column names and data types (dates, teams, odds, goals).
- Validate:
  - No duplicate matches
  - Correct season ordering
  - Missing values handled consistently

**Deliverable:** Clean, merged dataset + data dictionary.

---

## Step 2 — Feature engineering (past-only)
Create features using *only information available before each match*:
- Rolling team form (last 3/5/10 matches):
  - points, goals for/against, goal diff
- Home/away splits:
  - home form, away form
- Rest days, match congestion
- League position features (computed up to that date)
- Bookmaker-derived features:
  - implied probabilities from odds
  - odds movement (if available)

**Deliverable:** Feature table where every row is “match day safe” (no leakage).

---

## Step 3 — Train models with chronological splits
- Baseline models:
  - logistic regression (outcome)
  - poisson regression (goals) if predicting scores
- Strong models:
  - gradient boosting (XGBoost/LightGBM/CatBoost)
- Use time-based splits:
  - train on earlier seasons
  - validate on later seasons
  - never shuffle

**Deliverable:** Trained model artifacts + training config.

---

## Step 4 — Evaluate on holdout seasons
Evaluate on full seasons not used for training:
- If predicting probabilities (H/D/A):
  - log loss, Brier score, accuracy
- If predicting goals/scores:
  - RMSE/MAE for goals
- Calibration checks:
  - reliability curve
  - predicted vs actual win rates

**Deliverable:** Metrics report + plots + model comparison table.

---

## Step 5 — Reproducible pipeline + API-ready outputs
- Package workflow:
  - `data/` → `features/` → `train/` → `evaluate/`
- Save:
  - model + feature schema
  - inference script that takes upcoming fixtures and outputs predictions
- Optional:
  - FastAPI/Flask endpoint
  - scheduled retraining

**Deliverable:** Reproducible repo + prediction outputs (CSV/JSON) + inference entrypoint.

---

## Success criteria
- No data leakage (strict past-only features)
- Strong and stable holdout performance across seasons
- Fully reproducible runs from raw data → predictions