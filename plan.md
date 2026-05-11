# Implementation Plan - Fixture Matchup Prediction API

## Goal
Deliver a working ML-backed API that predicts a specific fixture matchup (for example, Manchester United vs Arsenal) with:

- expected home and away goals
- home win / draw / away win probabilities
- reproducible training pipeline
- Django REST inference endpoint
- minimal React + TypeScript UI for selecting two teams and viewing results

This plan is aligned to `requirements.md`.

---

## Delivery Window
Target: 10 working days (can compress to 5 with reduced scope).

---

## Build Order (Important)

1. Data model and ingestion first
2. Feature pipeline second
3. ML training third
4. Inference API fourth
5. Frontend last

No LLM training is involved.

---

## Phase Plan

## Phase 0 - Setup (Day 1)
Deliverables:
- Django + DRF + PostgreSQL project boots locally
- `apps/teams`, `apps/seasons`, `apps/matches`, `apps/ml` modules created
- Docker and environment configuration working

Acceptance:
- `docker compose up --build` works
- `python manage.py check` passes

## Phase 1 - Schema + Ingestion (Days 2-3)
Deliverables:
- Core models: `Team`, `Season`, `Match` (+ soft delete fields)
- Constraints and indexes in migrations
- `team_match_features` model/table for engineered features
- Ingestion script loads multi-season `E0.csv` data
- Clean season split artifacts (train/validation/holdout parquet)

Acceptance:
- At least 2016-17 to 2024-25 loaded/available for pipeline
- Invalid rows are dropped with log output
- No duplicate source matches 

## Phase 2 - Feature Engineering (Day 4)
Deliverables:
- Rolling 5-match features for home and away sides
- Leakage-safe implementation using strict chronological order and `shift(1)`
- Fixture-level feature join for model input

Acceptance:
- First-match rows have missing rolling stats as expected
- Unit test proves current match is not included in its own features

## Phase 3 - ML Training + Evaluation (Days 5-6)
Deliverables:
- `apps/ml/train.py` pipeline
- Baseline model (Ridge) and improved model (Gradient Boosting) trained
- Metrics tracked (MAE/RMSE for goals, log loss for outcome probabilities)
- Best model artifact and metadata saved in `artifacts/`

Acceptance:
- Reproducible training run from command line
- Artifact includes feature list + version + metrics

## Phase 4 - Inference API (Days 7-8)
Deliverables:
- `POST /api/predict/match` endpoint
- Input validation:
- home and away team must differ
- teams must exist
- enough history must exist to compute features
- Response contains expected goals, 3 probabilities, model version, feature snapshot
- Health endpoint confirms model loaded

Acceptance:
- Endpoint returns stable JSON and correct HTTP status codes
- Probability values are bounded and sum to ~1

## Phase 5 - Minimal Frontend (Day 9)
Deliverables:
- Team selectors (home and away)
- Predict action
- Result card for expected goals and probabilities
- strict TypeScript API types

Acceptance:
- `tsc --noEmit` passes
- UI handles loading and validation errors

## Phase 6 - Tests + Docs (Day 10)
Deliverables:
- Pytest coverage for:
- feature leakage prevention
- prediction input validation
- probability normalization
- auth/permission rules for admin routes
- README runbook for ingestion -> training -> serving -> UI

Acceptance:
- Clean-clone setup works with documented commands
- Test suite passes

---

## Endpoint Checklist

Public:
- `GET /api/teams/`
- `GET /api/seasons/`
- `GET /api/matches/?season=...`
- `GET /api/teams/{id}/form/?season=...`
- `POST /api/predict/match`
- `GET /api/health/`

Admin/Auth:
- `POST /api/auth/login/`
- `POST /api/admin/models/retrain/`
- `GET /api/admin/models/active/`

---

## Core Commands

```bash
python3 premier-league-api/data_ingestion.py
python3 -m apps.ml.train
python3 manage.py runserver
```

---

## 5-Day Compressed Option

If you must finish in 5 days, keep only:

- one model (Ridge)
- one prediction endpoint (`POST /api/predict/match`)
- no retrain admin endpoint
- minimal tests on leakage + input validation + probability sum
- very minimal frontend
