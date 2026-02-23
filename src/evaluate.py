from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np

from .data import read_or_build_matches
from .features import FEATURE_COLUMNS, build_features
from .modeling import build_main_model, compute_metrics, confusion_matrix_labels, encode_target
from .utils import append_run_log, ensure_dir, json_dump, load_config, set_global_seed, sort_seasons


def _metrics_by_season(features, proba, y_true):
    out = {}
    for season in sort_seasons(features["season"].unique().tolist()):
        mask = features["season"] == season
        if mask.sum() == 0:
            continue
        out[season] = compute_metrics(y_true[mask.values], proba[mask.values])
    return out


def _rolling_backtest(features, y, config):
    seasons = sort_seasons(features["season"].unique().tolist())
    rows = []

    for i in range(len(seasons) - 1):
        train_seasons = seasons[: i + 1]
        test_season = seasons[i + 1]

        X_train = features.loc[features["season"].isin(train_seasons), FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
        y_train = y[features["season"].isin(train_seasons).values]
        X_test = features.loc[features["season"] == test_season, FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
        y_test = y[features["season"] == test_season]

        if len(X_train) == 0 or len(X_test) == 0:
            continue

        model = build_main_model(seed=int(config["training"]["seed"]), model_cfg=config["model"])
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)
        metrics = compute_metrics(y_test.values if hasattr(y_test, "values") else y_test, proba)

        rows.append(
            {
                "train_up_to": train_seasons[-1],
                "test_season": test_season,
                **metrics,
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate EPL model on val/test and rolling backtest")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    set_global_seed(int(config["training"]["seed"]))

    report_dir = ensure_dir(config["paths"]["report_dir"])
    model_path = Path(config["paths"]["model_dir"]) / "model_latest.joblib"
    if not model_path.exists():
        raise FileNotFoundError("Model artifact not found. Run training first.")

    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_columns = artifact["feature_columns"]

    matches = read_or_build_matches(config)
    features = build_features(matches, config)
    y = encode_target(features["ftr"].values)

    split_cfg = config["split"]
    val_mask = features["season"].isin(split_cfg["validation_seasons"])
    test_mask = features["season"].isin(split_cfg["test_seasons"])

    X_val = features.loc[val_mask, feature_columns].replace([np.inf, -np.inf], np.nan)
    y_val = y[val_mask.values]
    X_test = features.loc[test_mask, feature_columns].replace([np.inf, -np.inf], np.nan)
    y_test = y[test_mask.values]

    val_proba = model.predict_proba(X_val)
    test_proba = model.predict_proba(X_test)

    val_metrics = compute_metrics(y_val, val_proba)
    test_metrics = compute_metrics(y_test, test_proba)

    cm = confusion_matrix_labels(y_test, test_proba)
    plot_warnings = None
    enable_plots = bool(config.get("reports", {}).get("enable_plots", False))
    if enable_plots:
        try:
            from .reporting import save_calibration_plot, save_confusion_matrix_plot

            save_confusion_matrix_plot(cm, str(report_dir / "confusion_matrix_test.png"))
            save_calibration_plot(y_test, test_proba, str(report_dir / "calibration_test.png"))
        except Exception as exc:
            plot_warnings = str(exc)
    else:
        plot_warnings = "Plot generation disabled by config."

    by_season_val = _metrics_by_season(features.loc[val_mask], val_proba, y[val_mask.values])
    by_season_test = _metrics_by_season(features.loc[test_mask], test_proba, y[test_mask.values])
    rolling = _rolling_backtest(features, y, config)

    report = {
        "selected_model_name": artifact.get("selected_model_name", "unknown"),
        "main_calibration_method": artifact.get("main_calibration_method", "unknown"),
        "validation": {"overall": val_metrics, "by_season": by_season_val},
        "test": {"overall": test_metrics, "by_season": by_season_test},
        "rolling_backtest": rolling,
        "plots": {
            "confusion_matrix_test": str(report_dir / "confusion_matrix_test.png"),
            "calibration_test": str(report_dir / "calibration_test.png"),
            "warning": plot_warnings,
        },
    }

    json_dump(report, report_dir / "evaluation_report.json")
    append_run_log(
        config["paths"]["run_log"],
        event="evaluate",
        payload={
            "selected_model": artifact.get("selected_model_name", "unknown"),
            "calibration": artifact.get("main_calibration_method", "unknown"),
            "val_accuracy": float(val_metrics["accuracy"]),
            "val_log_loss": float(val_metrics["log_loss"]),
            "test_accuracy": float(test_metrics["accuracy"]),
            "test_log_loss": float(test_metrics["log_loss"]),
            "test_brier": float(test_metrics["brier"]),
        },
    )
    print("Evaluation complete. Report saved to reports/evaluation_report.json")


if __name__ == "__main__":
    main()
