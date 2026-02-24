from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from src.data import read_or_build_matches
from src.features import build_fixture_features

from .models import ModelVersion, PredictionRequest, PredictionResult, Team
from .serializers import (
    ModelVersionSerializer,
    PredictionContractSerializer,
    PredictionCreateSerializer,
    PredictionResultSerializer,
)


MIN_HISTORY_MATCHES = 5
logger = logging.getLogger(__name__)


def _error_response(error: str, message: str, http_status: int) -> Response:
    return Response({"error": error, "message": message}, status=http_status)


def _flatten_error_message(detail) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            return _flatten_error_message(value)
        return "Invalid input."
    if isinstance(detail, (list, tuple)) and detail:
        return _flatten_error_message(detail[0])
    return str(detail or "Invalid input.")


def _resolve_config() -> dict:
    from src.utils import load_config

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
    return config


def _season_sort_key(season_label: str) -> int:
    return int(str(season_label).split("-")[0])


def _active_artifact():
    import joblib

    config = _resolve_config()
    model_path = Path(config["paths"]["model_dir"]) / "model_latest.joblib"
    if not model_path.exists():
        raise FileNotFoundError("Active model artifact not found. Run training first.")

    artifact = joblib.load(model_path)
    return config, model_path, artifact


def _metadata_file_exists(config: dict) -> bool:
    model_dir = Path(config["paths"]["model_dir"])
    report_dir = Path(config["paths"].get("report_dir", "reports"))
    return (model_dir / "metadata.json").exists() or (report_dir / "train_report.json").exists()


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


def _normalize_probabilities(raw_probs) -> tuple[float, float, float]:
    probs = np.asarray(raw_probs, dtype=float)
    probs = np.clip(probs, 0.0, 1.0)
    total = float(probs.sum())
    if not np.isfinite(total) or total <= 0:
        probs = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)
    else:
        probs = probs / total
    return float(probs[0]), float(probs[1]), float(probs[2])


def _estimate_expected_goals(feature_snapshot: dict, probs: tuple[float, float, float]) -> tuple[float, float]:
    # Lightweight heuristic for contract compatibility without retraining a goals model.
    home_for = float(feature_snapshot.get("home_goals_for_5") or 1.35)
    away_for = float(feature_snapshot.get("away_goals_for_5") or 1.35)
    home_against = float(feature_snapshot.get("home_goals_against_5") or 1.35)
    away_against = float(feature_snapshot.get("away_goals_against_5") or 1.35)
    elo_diff = float(feature_snapshot.get("elo_diff") or 0.0)
    rest_diff = float(feature_snapshot.get("rest_days_diff") or 0.0)

    p_home, p_draw, p_away = probs
    home_base = (home_for + away_against) / 2.0
    away_base = (away_for + home_against) / 2.0

    home_adj = 0.35 * (p_home - p_away) + 0.0004 * elo_diff + 0.02 * max(min(rest_diff, 5.0), -5.0)
    away_adj = 0.35 * (p_away - p_home) - 0.0004 * elo_diff - 0.02 * max(min(rest_diff, 5.0), -5.0)
    draw_pull = 0.15 * p_draw

    expected_home = float(np.clip(home_base + home_adj + draw_pull, 0.0, 6.0))
    expected_away = float(np.clip(away_base + away_adj + draw_pull, 0.0, 6.0))
    return round(expected_home, 4), round(expected_away, 4)


def _history_count(matches: pd.DataFrame, team_name: str, before_date) -> int:
    match_date = pd.Timestamp(before_date)
    prior = matches[matches["match_date"] < match_date]
    if prior.empty:
        return 0
    mask = (prior["home_team"] == team_name) | (prior["away_team"] == team_name)
    return int(mask.sum())


def _build_prediction_contract_payload(result: PredictionResult) -> dict:
    features = result.features_json or {}
    probs = _normalize_probabilities([result.p_home, result.p_draw, result.p_away])
    expected_home, expected_away = _estimate_expected_goals(features, probs)
    p_home, p_draw, p_away = probs

    return {
        "home_team": result.request.home_team.name,
        "away_team": result.request.away_team.name,
        "expected_home_goals": expected_home,
        "expected_away_goals": expected_away,
        "home_win_probability": p_home,
        "draw_probability": p_draw,
        "away_win_probability": p_away,
        "model_version": result.model_version.version,
        "features": features,
    }


def _load_matches_or_error():
    try:
        config = _resolve_config()
        matches = read_or_build_matches(config)
        return config, matches, None
    except FileNotFoundError as exc:
        logger.warning("data_load_failed_missing_file", extra={"error": str(exc)})
        return None, None, _error_response("data_not_found", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:  # pragma: no cover - defensive envelope guard
        logger.exception("data_load_failed", extra={"error": str(exc)})
        return None, None, _error_response("data_load_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def health(request):
    try:
        config, _, artifact = _active_artifact()
    except FileNotFoundError:
        logger.warning("health_model_not_loaded")
        return Response(
            {"status": "error", "error": "model_not_loaded", "artifact_loaded": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:  # pragma: no cover - defensive envelope guard
        logger.exception("health_check_failed", extra={"error": str(exc)})
        return Response(
            {"status": "error", "error": "model_not_loaded", "artifact_loaded": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    feature_list = artifact.get("feature_columns") or []
    if not feature_list:
        logger.warning("health_feature_list_missing")
        return Response(
            {"status": "error", "error": "feature_list_missing", "artifact_loaded": True},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if not _metadata_file_exists(config):
        logger.warning("health_metadata_missing")
        return Response(
            {"status": "error", "error": "metadata_missing", "artifact_loaded": True},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "status": "ok",
            "artifact_loaded": True,
            "model_version": str(artifact.get("trained_at") or artifact.get("version") or "unknown"),
        }
    )


@api_view(["GET"])
def list_teams(request):
    _, matches, err = _load_matches_or_error()
    if err is not None:
        return err

    team_names = sorted(set(matches["home_team"].dropna().tolist()) | set(matches["away_team"].dropna().tolist()))
    data = [{"id": idx, "name": name} for idx, name in enumerate(team_names, start=1)]
    return Response(data)


@api_view(["GET"])
def list_seasons(request):
    _, matches, err = _load_matches_or_error()
    if err is not None:
        return err

    seasons = sorted(matches["season"].dropna().astype(str).unique().tolist(), key=_season_sort_key)
    data = [{"label": season} for season in seasons]
    return Response(data)


@api_view(["GET"])
def list_matches(request):
    _, matches, err = _load_matches_or_error()
    if err is not None:
        return err

    season = (request.query_params.get("season") or "").strip()
    filtered = matches
    if season:
        filtered = matches[matches["season"].astype(str) == season]
        if filtered.empty:
            return _error_response("not_found", f"Season '{season}' not found.", status.HTTP_404_NOT_FOUND)

    cols = ["season", "match_date", "home_team", "away_team", "home_goals", "away_goals", "ftr"]
    if "match_id" in filtered.columns:
        cols = ["match_id"] + cols
    out = filtered.loc[:, [c for c in cols if c in filtered.columns]].copy().sort_values(
        ["match_date", "home_team", "away_team"]
    )
    if "match_date" in out.columns:
        out["match_date"] = pd.to_datetime(out["match_date"]).dt.strftime("%Y-%m-%d")
    return Response(out.to_dict(orient="records"))


@api_view(["POST"])
def create_prediction(request):
    ser = PredictionCreateSerializer(data=request.data)
    if not ser.is_valid():
        logger.warning("prediction_validation_failed", extra={"errors": str(ser.errors)})
        return _error_response("invalid_input", _flatten_error_message(ser.errors), status.HTTP_400_BAD_REQUEST)
    payload = ser.validated_data
    home_name = payload["home_team"].strip()
    away_name = payload["away_team"].strip()
    logger.info(
        "prediction_request",
        extra={"home_team": home_name, "away_team": away_name, "match_date": str(payload["match_date"])},
    )

    try:
        config, model_path, artifact = _active_artifact()
    except FileNotFoundError as exc:
        logger.warning("prediction_model_load_failed", extra={"error": str(exc)})
        return _error_response("model_not_found", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:  # pragma: no cover - defensive envelope guard
        logger.exception("prediction_unavailable", extra={"error": str(exc)})
        return _error_response("prediction_unavailable", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    matches = read_or_build_matches(config)
    home_team = Team.objects.filter(name=home_name).first()
    if home_team is None:
        logger.warning("prediction_unknown_team", extra={"team_role": "home", "team_name": home_name})
        return _error_response("not_found", f"Home team '{home_name}' does not exist.", status.HTTP_404_NOT_FOUND)
    away_team = Team.objects.filter(name=away_name).first()
    if away_team is None:
        logger.warning("prediction_unknown_team", extra={"team_role": "away", "team_name": away_name})
        return _error_response("not_found", f"Away team '{away_name}' does not exist.", status.HTTP_404_NOT_FOUND)

    history_matches = matches[matches["match_date"] < pd.Timestamp(payload["match_date"])].copy()
    if (
        _history_count(matches, home_name, payload["match_date"]) < MIN_HISTORY_MATCHES
        or _history_count(matches, away_name, payload["match_date"]) < MIN_HISTORY_MATCHES
    ):
        logger.warning(
            "prediction_insufficient_history",
            extra={"home_team": home_name, "away_team": away_name, "match_date": str(payload["match_date"])},
        )
        return _error_response(
            "insufficient_history",
            "Not enough historical matches to compute rolling features.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    fixtures_df = np.array(
        [
            (
                payload["match_date"],
                home_name,
                away_name,
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
    fixtures_df = pd.DataFrame(fixtures_df)
    fixture_features = build_fixture_features(history_matches, fixtures_df, config)
    if fixture_features.empty:
        logger.warning(
            "prediction_feature_build_failed",
            extra={"home_team": home_name, "away_team": away_name, "match_date": str(payload["match_date"])},
        )
        return _error_response(
            "insufficient_history",
            "Not enough historical matches to compute rolling features.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    model = artifact["model"]
    feature_cols = artifact["feature_columns"]
    X = fixture_features[feature_cols]
    probs = model.predict_proba(X)[0]
    p_home, p_draw, p_away = _normalize_probabilities(probs)
    outcomes = ["H", "D", "A"]
    predicted_outcome = outcomes[int(np.argmax([p_home, p_draw, p_away]))]
    feature_snapshot = _json_safe_feature_snapshot(fixture_features.iloc[0].to_dict())

    with transaction.atomic():
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
            features_json=feature_snapshot,
        )

    contract_payload = _build_prediction_contract_payload(result)
    return Response(PredictionContractSerializer(contract_payload).data, status=status.HTTP_201_CREATED)


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
        return _error_response("not_found", "Prediction not found.", status.HTTP_404_NOT_FOUND)
    return Response(PredictionResultSerializer(result).data)


@api_view(["GET"])
def active_model(request):
    model = ModelVersion.objects.filter(is_active=True).order_by("-created_at").first()
    if not model:
        return _error_response("not_found", "No active model version saved yet.", status.HTTP_404_NOT_FOUND)
    return Response(ModelVersionSerializer(model).data)


class AdminTokenRequiredPermission(BasePermission):
    message = "Authentication token is required."

    def has_permission(self, request, view):
        try:
            auth_result = TokenAuthentication().authenticate(request)
        except Exception:
            return False
        if not auth_result:
            return False
        user, token = auth_result
        request._user = user
        request._auth = token
        return bool(user and user.is_authenticated)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AdminTokenRequiredPermission])
def admin_active_model(request):
    return active_model(request)
