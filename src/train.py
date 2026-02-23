from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .data import read_or_build_matches
from .features import FEATURE_COLUMNS, build_features
from .modeling import (
    CLASS_ORDER,
    compute_metrics,
    encode_target,
    fit_and_calibrate_main,
    fit_logistic_baseline,
    fit_most_common_baseline,
)
from .utils import append_run_log, dataframe_hash, ensure_dir, json_dump, load_config, set_global_seed


def _season_mask(series: pd.Series, seasons: list[str]) -> pd.Series:
    return series.isin(seasons)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train leakage-safe EPL 1X2 model")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    set_global_seed(int(config["training"]["seed"]))

    model_dir = ensure_dir(config["paths"]["model_dir"])
    report_dir = ensure_dir(config["paths"]["report_dir"])
    processed_dir = ensure_dir(Path(config["paths"]["processed_matches"]).parent)

    matches = read_or_build_matches(config)
    features = build_features(matches, config)
    features_path = Path(config["paths"]["features_table"])
    features_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(features_path, index=False)

    y = encode_target(features["ftr"].values)
    X = features[FEATURE_COLUMNS].copy()

    # Fill optional implied-odds features with train-safe default later via model pipeline,
    # but ensure finite numeric matrix for fallback estimators.
    X = X.replace([np.inf, -np.inf], np.nan)

    split_cfg = config["split"]
    train_mask = _season_mask(features["season"], split_cfg["train_seasons"])
    val_mask = _season_mask(features["season"], split_cfg["validation_seasons"])
    test_mask = _season_mask(features["season"], split_cfg["test_seasons"])

    if train_mask.sum() == 0 or val_mask.sum() == 0 or test_mask.sum() == 0:
        raise ValueError("Split masks are empty. Check season split configuration.")

    X_train, y_train = X.loc[train_mask], y[train_mask.values]
    X_val, y_val = X.loc[val_mask], y[val_mask.values]

    baseline_common = fit_most_common_baseline(y_train)
    baseline_common_val_proba = baseline_common.predict_proba(X_val)
    baseline_common_metrics = compute_metrics(y_val, baseline_common_val_proba)

    baseline_logit = fit_logistic_baseline(X_train, y_train, seed=int(config["training"]["seed"]))
    baseline_logit_val_proba = baseline_logit.predict_proba(X_val)
    baseline_logit_metrics = compute_metrics(y_val, baseline_logit_val_proba)

    main_model, calibration_method, main_val_metrics = fit_and_calibrate_main(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        seed=int(config["training"]["seed"]),
        model_cfg=config["model"],
        calibration_methods=config["training"].get("calibration_methods", ["sigmoid"]),
    )

    # Select deployable model by validation log loss among logistic baseline vs main.
    candidates = [
        ("most_common", baseline_common, baseline_common_metrics),
        ("logistic", baseline_logit, baseline_logit_metrics),
        ("main_gb", main_model, main_val_metrics),
    ]
    candidates.sort(key=lambda t: t[2]["log_loss"])
    selected_name, selected_model, selected_metrics = candidates[0]

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_path = model_dir / f"model_{run_ts}.joblib"
    latest_model_path = model_dir / "model_latest.joblib"

    payload = {
        "model": selected_model,
        "feature_columns": FEATURE_COLUMNS,
        "class_order": CLASS_ORDER,
        "selected_model_name": selected_name,
        "main_calibration_method": calibration_method,
        "split": split_cfg,
        "training_seed": int(config["training"]["seed"]),
        "config": config,
        "data_hash": dataframe_hash(features[["season", "match_date", "home_team", "away_team", "ftr"]]),
        "trained_at": run_ts,
    }
    joblib.dump(payload, model_path)
    joblib.dump(payload, latest_model_path)

    report = {
        "run_id": run_ts,
        "n_rows": int(len(features)),
        "split_counts": {
            "train": int(train_mask.sum()),
            "validation": int(val_mask.sum()),
            "test": int(test_mask.sum()),
        },
        "validation_metrics": {
            "most_common": baseline_common_metrics,
            "logistic": baseline_logit_metrics,
            "main_gradient_boosting": main_val_metrics,
            "selected": {
                "name": selected_name,
                "metrics": selected_metrics,
            },
        },
        "artifacts": {
            "model_versioned": str(model_path),
            "model_latest": str(latest_model_path),
            "features_table": str(features_path),
        },
    }

    json_dump(report, report_dir / "train_report.json")
    append_run_log(
        config["paths"]["run_log"],
        event="train",
        payload={
            "run_id": run_ts,
            "selected_model": selected_name,
            "calibration": calibration_method,
            "val_accuracy": float(selected_metrics["accuracy"]),
            "val_log_loss": float(selected_metrics["log_loss"]),
            "val_brier": float(selected_metrics["brier"]),
            "n_rows": int(len(features)),
        },
    )
    print(f"Training complete. Selected model: {selected_name}")
    print(f"Saved model: {model_path}")


if __name__ == "__main__":
    main()
