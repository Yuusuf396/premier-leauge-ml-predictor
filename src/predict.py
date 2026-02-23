from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from .data import read_fixtures_csv, read_or_build_matches
from .features import build_fixture_features
from .modeling import INT_TO_CLASS
from .utils import append_run_log, ensure_dir, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixture-level 1X2 predictions")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--fixtures", required=True, help="CSV of upcoming fixtures")
    parser.add_argument("--output", default="reports/predictions.csv", help="Output CSV path")
    args = parser.parse_args()

    config = load_config(args.config)
    model_path = Path(config["paths"]["model_dir"]) / "model_latest.joblib"
    if not model_path.exists():
        raise FileNotFoundError("Model artifact not found. Run training first.")

    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_columns = artifact["feature_columns"]

    history = read_or_build_matches(config)
    fixtures = read_fixtures_csv(args.fixtures)
    fixture_features = build_fixture_features(history, fixtures, config)

    X_pred = fixture_features[feature_columns]
    proba = model.predict_proba(X_pred)
    pred_idx = proba.argmax(axis=1)

    out = fixture_features[["match_date", "home_team", "away_team"]].copy()
    out["P_home"] = proba[:, 0]
    out["P_draw"] = proba[:, 1]
    out["P_away"] = proba[:, 2]
    out["predicted_outcome"] = [INT_TO_CLASS[int(i)] for i in pred_idx]
    out["model_version"] = artifact.get("trained_at", "unknown")

    out_path = Path(args.output)
    ensure_dir(out_path.parent)
    out.to_csv(out_path, index=False)
    append_run_log(
        config["paths"]["run_log"],
        event="predict",
        payload={
            "fixtures_file": args.fixtures,
            "predictions_file": str(out_path),
            "n_predictions": int(len(out)),
            "model_version": artifact.get("trained_at", "unknown"),
        },
    )
    print(f"Saved predictions: {out_path}")


if __name__ == "__main__":
    main()
