# Premier League Fixture Prediction API

## Overview

This project is a production-oriented backend that predicts a specific fixture matchup, for example:

- Manchester United (home) vs Arsenal (away)

It is not a simple standings API and not only a winner label API.
The core output is a matchup prediction package:

- expected home goals
- expected away goals
- home win / draw / away win probabilities
- model version and feature snapshot used for inference

Built with Django REST Framework, PostgreSQL, and a minimal React + TypeScript client.

---

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework |
| Database | PostgreSQL 15 |
| ML | scikit-learn (Ridge + Gradient Boosting baseline comparison) |
| Auth | DRF Token Authentication (admin/training routes only) |
| Filtering | django-filter |
| Frontend | React 18 + TypeScript (strict) |
| Dev environment | Docker + docker-compose |
| Tests | pytest + pytest-django |

---

## Product Scope

### Core Product Behavior

Given a fixture payload:

```json
{
  "home_team": "Manchester United",
  "away_team": "Arsenal",
  "season": "2025-26",
  "match_date": "2026-03-15"
}
```

The API returns:

```json
{
  "home_team": "Manchester United",
  "away_team": "Arsenal",
  "expected_home_goals": 1.42,
  "expected_away_goals": 1.31,
  "home_win_probability": 0.39,
  "draw_probability": 0.28,
  "away_win_probability": 0.33,
  "model_version": "fixture_model_v1_20260220",
  "features": {
    "home_rolling_points_5": 2.0,
    "away_rolling_points_5": 2.2,
    "home_rolling_goal_diff_5": 0.8,
    "away_rolling_goal_diff_5": 1.0,
    "home_rest_days": 6,
    "away_rest_days": 7
  }
}
```

Probabilities must sum to 1.0 (within floating-point tolerance).

### Out of Scope (MVP)

- Player-level predictions
- In-game/live minute-by-minute predictions
- External betting odds ingestion
- Background queue infrastructure
- Multi-service auth (JWT/OAuth)

---

## Data Source

Historical CSV seasons from football-data.co.uk (`E0.csv` format), starting from at least:

- training: 2016-17 to 2022-23
- validation: 2023-24
- holdout: 2024-25

The 2025-26 season is for fresh inference once enough matches exist.

---

## Project Structure

```text
premier-league-api/
  config/
    settings.py
    urls.py
  apps/
    teams/
    seasons/
    matches/
    ml/
      feature_pipeline.py
      train.py
      predictor.py
      views.py
      tests/
  data/
    raw/seasons/
    processed/
  artifacts/
    model.joblib
    metadata.json
  frontend/
    src/
      types/api.ts
      hooks/
      components/
  data_ingestion.py
```

---

## Database Requirements

### teams
- id, name (unique), short_name (unique), is_active

### seasons
- id, label (unique), start_date, end_date, is_current
- partial unique index to enforce only one current season

### matches
- season_id, home_team_id, away_team_id, matchday, match_date, kickoff_time
- home_score, away_score, status
- no self-match constraint
- completed match requires non-null scores
- soft delete fields (`is_deleted`, `deleted_at`)

### team_match_features
- team_id, opponent_id, match_id
- rolling points/goals/xg features (shifted by 1 match)
- rest days, home/away flag
- target columns for training

---

## ML Requirements

### Feature Engineering

- Strict chronological ordering
- Rolling window size = 5
- `shift(1)` for all rolling features to prevent leakage
- Home and away perspective features are computed separately and then joined for fixture inference

### Targets

Two related targets:

1. expected goals for each side (regression)
2. outcome probabilities (home win / draw / away win), derived from model outputs

### Training

- Train baseline and improved models:
- Ridge (baseline)
- Gradient Boosting (improved)
- Chronological split only; no random split
- Metrics:
- MAE/RMSE for expected goals
- log loss and calibration quality for probabilities

### Artifact Management

Saved artifacts include:

- trained model
- preprocessing objects/scalers
- feature list
- metadata (train window, validation metrics, timestamp, version)

---

## API Requirements

### Public Endpoints

- `GET /api/teams/`
- `GET /api/seasons/`
- `GET /api/matches/?season=...`
- `GET /api/teams/{id}/form/?season=...` (context endpoint)
- `POST /api/predict/match` (core endpoint)
- `GET /api/health/`

### Admin/Auth Endpoints

- `POST /api/auth/login/`
- `POST /api/admin/models/retrain/`
- `GET /api/admin/models/active/`
- existing match/team admin CRUD endpoints (token-protected)

Non-admin token on admin routes returns `403`.

### Error Envelope

All API errors return:

```json
{
  "error": "invalid_input",
  "message": "Home team and away team must be different."
}
```

No stack traces in responses.

---

## Frontend Requirements

Minimal UI only:

- Home team selector
- Away team selector
- Predict button
- Prediction result card with expected goals and 3 probabilities
- Basic loading and error states

TypeScript strict mode with no `any`.

---

## Testing Requirements

Must include tests for:

- leakage prevention in feature pipeline (`shift(1)` behavior)
- inference input validation (same team, unknown teams, insufficient history)
- probability normalization (sum near 1)
- regression metric computation path
- auth and permission rules for retraining/admin routes

---

## Environment Variables

```env
DEBUG=True
SECRET_KEY=change-me
DATABASE_URL=postgres://pluser:password@db:5432/pldb
ALLOWED_HOSTS=localhost,127.0.0.1
MODEL_ARTIFACT_PATH=artifacts/model.joblib
```
