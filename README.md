# Premier League 1X2 Prediction Pipeline

Leakage-safe, season-aware machine-learning pipeline for Premier League fixture prediction.

## What it does

- Trains 1X2 outcome models (Home / Draw / Away)
- Produces calibrated probabilities `P(Home)`, `P(Draw)`, `P(Away)`
- Uses strict past-only features (rolling windows + chronological updates)
- Evaluates with fixed splits and rolling backtest
- Runs inference on upcoming fixtures CSV

## Repo structure

```text
.
├── config.yaml
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── reports/
├── src/
│   ├── __init__.py
│   ├── data.py
│   ├── evaluate.py
│   ├── features.py
│   ├── modeling.py
│   ├── predict.py
│   ├── reporting.py
│   ├── train.py
│   └── utils.py
└── premier-league-api/
    └── data/raw/seasons/*.csv
```

## Data requirements

Place season files in:

`premier-league-api/data/raw/seasons/`

Expected filenames:

- `2016-17.csv`, ..., `2025-26.csv`

Required columns in each CSV:

- `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`

Optional columns:

- `FTR`
- odds triplets (e.g. `B365H/B365D/B365A`)

Pipeline works if odds are missing.

## Install dependencies

```bash
pip install pandas numpy scikit-learn pyyaml joblib matplotlib
```

Optional for stronger main model:

```bash
pip install lightgbm
# or
pip install xgboost
```

## Train

```bash
python -m src.train --config config.yaml
```

Outputs:

- `models/model_latest.joblib`
- `models/model_<timestamp>.joblib`
- `data/processed/matches_clean.parquet`
- `data/processed/features_table.parquet`
- `reports/train_report.json`

## Evaluate

```bash
python -m src.evaluate --config config.yaml
```

Outputs:

- `reports/evaluation_report.json`
- `reports/confusion_matrix_test.png`
- `reports/calibration_test.png`

## Predict upcoming fixtures

Create a fixtures CSV, e.g. `fixtures.csv`:

```csv
Date,HomeTeam,AwayTeam
2026-03-15,Manchester United,Arsenal
2026-03-15,Liverpool,Chelsea
```

Run:

```bash
python -m src.predict --config config.yaml --fixtures fixtures.csv
```

Output:

- `reports/predictions.csv`

## Leakage safeguards implemented

- Feature generation is chronological and stateful (`build_features`)
- All rolling features are computed before current match update
- Explicit assertion checks ensure no history date is `>=` current feature date
- No shuffled splits; season-based chronological train/val/test

## Split policy (default in config)

- Train: 2016-17 to 2022-23
- Validation: 2023-24
- Test: 2024-25 and 2025-26

Also includes rolling backtest: train up to season `S`, test on `S+1`.
