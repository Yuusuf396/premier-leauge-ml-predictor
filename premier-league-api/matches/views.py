from __future__ import annotations

from pathlib import Path
import math

import joblib
import numpy as np
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from src.data import read_or_build_matches
from src.features import build_fixture_features
from src.utils import load_config

from .models import ModelVersion, PredictionRequest, PredictionResult, Team
from .serializers import ModelVersionSerializer, PredictionCreateSerializer, PredictionResultSerializer


def _active_artifact():
    config_path = Path(settings.ML_CONFIG_PATH)
    config = load_config(config_path)
    config_root = config_path.parent
    for key in ["model_dir", "raw_glob", "processed_matches", "features_table", "report_dir", "run_log"]:
        path_value = config["paths"].get(key)
        if not path_value:
            continue
        p = Path(path_value)
        if not p.is_absolute():
            config["paths"][key] = str(config_root / p)

    model_path = Path(config["paths"]["model_dir"]) / "model_latest.joblib"
    if not model_path.exists():
        raise FileNotFoundError("Active model artifact not found. Run training first.")

    artifact = joblib.load(model_path)
    return config, model_path, artifact


def _upsert_model_version(model_path: Path, artifact: dict) -> ModelVersion:
    version = artifact.get("trained_at", "unknown")
    train_report = Path("reports/train_report.json")
    val_log_loss = None
    val_accuracy = None
    if train_report.exists():
        import json

        payload = json.loads(train_report.read_text(encoding="utf-8"))
        selected = payload.get("validation_metrics", {}).get("selected", {}).get("metrics", {})
        val_log_loss = selected.get("log_loss")
        val_accuracy = selected.get("accuracy")

    obj, _ = ModelVersion.objects.update_or_create(
        version=version,
        defaults={
            "artifact_path": str(model_path),
            "selected_model_name": artifact.get("selected_model_name", ""),
            "calibration_method": artifact.get("main_calibration_method", ""),
            "val_log_loss": val_log_loss,
            "val_accuracy": val_accuracy,
            "is_active": True,
        },
    )
    ModelVersion.objects.exclude(id=obj.id).update(is_active=False)
    return obj


def _json_safe_feature_snapshot(row_dict: dict) -> dict:
    out = {}
    for key, value in row_dict.items():
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        elif isinstance(value, float) and math.isnan(value):
            out[key] = None
        else:
            out[key] = value
    return out


@api_view(["POST"])
def create_prediction(request):
    ser = PredictionCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    payload = ser.validated_data

    try:
        config, model_path, artifact = _active_artifact()
    except FileNotFoundError as exc:
        return Response({"error": "model_not_found", "message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    matches = read_or_build_matches(config)
    fixtures_df = np.array(
        [
            (
                payload["match_date"],
                payload["home_team"].strip(),
                payload["away_team"].strip(),
                np.nan,
                np.nan,
                np.nan,
            )
        ],
        dtype=[
            ("match_date", "O"),
            ("home_team", "O"),
            ("away_team", "O"),
            ("odds_home", "f8"),
            ("odds_draw", "f8"),
            ("odds_away", "f8"),
        ],
    )
    import pandas as pd

    fixtures_df = pd.DataFrame(fixtures_df)
    fixture_features = build_fixture_features(matches, fixtures_df, config)
    if fixture_features.empty:
        return Response(
            {"error": "feature_build_failed", "message": "Could not build features for this fixture."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    model = artifact["model"]
    feature_cols = artifact["feature_columns"]
    X = fixture_features[feature_cols]
    probs = model.predict_proba(X)[0]
    p_home, p_draw, p_away = float(probs[0]), float(probs[1]), float(probs[2])
    outcomes = ["H", "D", "A"]
    predicted_outcome = outcomes[int(np.argmax(probs))]

    with transaction.atomic():
        home_team, _ = Team.objects.get_or_create(name=payload["home_team"].strip())
        away_team, _ = Team.objects.get_or_create(name=payload["away_team"].strip())
        model_version = _upsert_model_version(model_path, artifact)

        req = PredictionRequest.objects.create(
            home_team=home_team,
            away_team=away_team,
            match_date=payload["match_date"],
        )
        result = PredictionResult.objects.create(
            request=req,
            model_version=model_version,
            p_home=p_home,
            p_draw=p_draw,
            p_away=p_away,
            predicted_outcome=predicted_outcome,
            features_json=_json_safe_feature_snapshot(fixture_features.iloc[0].to_dict()),
        )

    return Response(PredictionResultSerializer(result).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def list_predictions(request):
    qs = PredictionResult.objects.select_related("request", "request__home_team", "request__away_team", "model_version").all()
    return Response(PredictionResultSerializer(qs, many=True).data)


@api_view(["GET"])
def prediction_detail(request, prediction_id: int):
    try:
        result = PredictionResult.objects.select_related(
            "request", "request__home_team", "request__away_team", "model_version"
        ).get(id=prediction_id)
    except PredictionResult.DoesNotExist:
        return Response({"error": "not_found", "message": "Prediction not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(PredictionResultSerializer(result).data)


@api_view(["GET"])
def active_model(request):
    model = ModelVersion.objects.filter(is_active=True).order_by("-created_at").first()
    if not model:
        return Response({"error": "not_found", "message": "No active model version saved yet."}, status=status.HTTP_404_NOT_FOUND)
    return Response(ModelVersionSerializer(model).data)
