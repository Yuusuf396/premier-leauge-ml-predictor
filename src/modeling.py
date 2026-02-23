from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CLASS_ORDER = ["H", "D", "A"]
CLASS_TO_INT = {c: i for i, c in enumerate(CLASS_ORDER)}
INT_TO_CLASS = {i: c for c, i in CLASS_TO_INT.items()}


@dataclass
class ConstantOutcomeModel:
    probs: np.ndarray

    def predict_proba(self, X):
        n = len(X)
        return np.tile(self.probs, (n, 1))

    def predict(self, X):
        idx = int(np.argmax(self.probs))
        return np.full(len(X), idx)


def encode_target(y_labels) -> np.ndarray:
    return np.array([CLASS_TO_INT[v] for v in y_labels], dtype=int)


def multiclass_brier_score(y_true: np.ndarray, proba: np.ndarray, n_classes: int = 3) -> float:
    one_hot = np.eye(n_classes)[y_true]
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def compute_metrics(y_true: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    pred = np.argmax(proba, axis=1)
    return {
        "log_loss": float(log_loss(y_true, proba, labels=[0, 1, 2])),
        "accuracy": float(accuracy_score(y_true, pred)),
        "brier": float(multiclass_brier_score(y_true, proba, n_classes=3)),
    }


def fit_most_common_baseline(y_train: np.ndarray) -> ConstantOutcomeModel:
    counts = np.bincount(y_train, minlength=3).astype(float)
    probs = counts / counts.sum()
    return ConstantOutcomeModel(probs=probs)


def fit_logistic_baseline(X_train, y_train, seed: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    multi_class="multinomial",
                    solver="lbfgs",
                    max_iter=2000,
                    random_state=seed,
                ),
            ),
        ]
    ).fit(X_train, y_train)


def build_main_model(seed: int, model_cfg: dict[str, Any]):
    # Preferred: LightGBM
    try:
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            objective="multiclass",
            num_class=3,
            n_estimators=int(model_cfg.get("n_estimators", 400)),
            learning_rate=float(model_cfg.get("learning_rate", 0.03)),
            max_depth=int(model_cfg.get("max_depth", -1)),
            subsample=float(model_cfg.get("subsample", 0.9)),
            colsample_bytree=float(model_cfg.get("colsample_bytree", 0.9)),
            random_state=seed,
            n_jobs=-1,
        )
    except Exception:
        pass

    # Fallback: XGBoost
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=int(model_cfg.get("n_estimators", 500)),
            learning_rate=float(model_cfg.get("learning_rate", 0.03)),
            max_depth=int(model_cfg.get("xgb_max_depth", 5)),
            subsample=float(model_cfg.get("subsample", 0.9)),
            colsample_bytree=float(model_cfg.get("colsample_bytree", 0.9)),
            random_state=seed,
            eval_metric="mlogloss",
            n_jobs=-1,
        )
    except Exception:
        pass

    # Last-resort fallback keeps pipeline runnable even without extra libs.
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.pipeline import Pipeline

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_depth=int(model_cfg.get("hist_max_depth", 6)),
                    learning_rate=float(model_cfg.get("learning_rate", 0.03)),
                    max_iter=int(model_cfg.get("n_estimators", 400)),
                    random_state=seed,
                ),
            ),
        ]
    )


def fit_and_calibrate_main(
    X_train,
    y_train,
    X_val,
    y_val,
    seed: int,
    model_cfg: dict[str, Any],
    calibration_methods: list[str] | None = None,
) -> tuple[Any, str, dict[str, float]]:
    base = build_main_model(seed=seed, model_cfg=model_cfg)
    base.fit(X_train, y_train)

    calibrators: list[tuple[str, Any]] = [("none", base)]

    methods = calibration_methods or ["sigmoid"]
    for method in methods:
        if method == "none":
            continue
        try:
            cal = CalibratedClassifierCV(base, method=method, cv="prefit")
            cal.fit(X_val, y_val)
            calibrators.append((method, cal))
        except Exception as exc:
            print(f"Calibration method '{method}' skipped: {exc}")

    scored: list[tuple[str, Any, dict[str, float]]] = []
    for method, model in calibrators:
        proba = model.predict_proba(X_val)
        metrics = compute_metrics(y_val, proba)
        scored.append((method, model, metrics))

    scored.sort(key=lambda x: x[2]["log_loss"])
    best_method, best_model, best_metrics = scored[0]
    return best_model, best_method, best_metrics


def confusion_matrix_labels(y_true: np.ndarray, proba: np.ndarray) -> np.ndarray:
    y_pred = np.argmax(proba, axis=1)
    return confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
