from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from matches.models import ModelVersion, Team


class _FakeModel:
    def predict_proba(self, X):
        return np.array([[2.0, 1.0, 1.0]], dtype=float)


def _fake_artifact_bundle():
    artifact = {
        "model": _FakeModel(),
        "feature_columns": ["home_points_5", "away_points_5"],
        "trained_at": "test-model-v1",
        "selected_model_name": "fake",
        "main_calibration_method": "none",
    }
    return {"paths": {}}, Path("models/model_latest.joblib"), artifact


def _history_df(match_count_per_team: int = 5) -> pd.DataFrame:
    rows = []
    base_date = pd.Timestamp("2024-01-01")
    for i in range(match_count_per_team):
        rows.append(
            {
                "match_date": base_date + pd.Timedelta(days=i),
                "home_team": "Arsenal",
                "away_team": f"OpponentA{i}",
            }
        )
        rows.append(
            {
                "match_date": base_date + pd.Timedelta(days=i + 1),
                "home_team": f"OpponentM{i}",
                "away_team": "Manchester United",
            }
        )
    return pd.DataFrame(rows)


def _fixture_features_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "home_points_5": 2.0,
                "away_points_5": 1.8,
                "home_goals_for_5": 1.6,
                "away_goals_for_5": 1.2,
                "home_goals_against_5": 1.0,
                "away_goals_against_5": 1.1,
                "elo_diff": 45.0,
                "rest_days_diff": 1.0,
            }
        ]
    )


class PredictionApiContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.predict_url = "/api/predict/match"
        self.health_url = "/api/health/"
        self.admin_active_model_url = "/api/admin/models/active/"

    def test_same_team_validation_returns_structured_error(self):
        response = self.client.post(
            self.predict_url,
            {
                "home_team": "Arsenal",
                "away_team": "Arsenal",
                "match_date": "2026-03-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_input")
        self.assertIn("different", response.json()["message"].lower())

    @patch("matches.views.build_fixture_features")
    @patch("matches.views.read_or_build_matches")
    @patch("matches.views._active_artifact")
    def test_prediction_probabilities_are_normalized(self, mock_active_artifact, mock_read_matches, mock_build_features):
        Team.objects.create(name="Manchester United")
        Team.objects.create(name="Arsenal")

        mock_active_artifact.return_value = _fake_artifact_bundle()
        mock_read_matches.return_value = _history_df(match_count_per_team=6)
        mock_build_features.return_value = _fixture_features_df()

        response = self.client.post(
            self.predict_url,
            {
                "home_team": "Manchester United",
                "away_team": "Arsenal",
                "match_date": "2026-03-15",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        total = (
            payload["home_win_probability"]
            + payload["draw_probability"]
            + payload["away_win_probability"]
        )
        self.assertAlmostEqual(total, 1.0, places=6)
        self.assertGreaterEqual(payload["home_win_probability"], 0.0)
        self.assertGreaterEqual(payload["draw_probability"], 0.0)
        self.assertGreaterEqual(payload["away_win_probability"], 0.0)
        self.assertLessEqual(payload["home_win_probability"], 1.0)
        self.assertLessEqual(payload["draw_probability"], 1.0)
        self.assertLessEqual(payload["away_win_probability"], 1.0)
        self.assertLess(abs(total - 1.0), 1e-6)
        self.assertIn("expected_home_goals", payload)
        self.assertIn("expected_away_goals", payload)
        self.assertIn("features", payload)

    @patch("matches.views._active_artifact")
    def test_unknown_team_returns_404_error_envelope(self, mock_active_artifact):
        Team.objects.create(name="Arsenal")
        mock_active_artifact.return_value = _fake_artifact_bundle()

        with patch("matches.views.read_or_build_matches", return_value=_history_df(match_count_per_team=6)):
            response = self.client.post(
                self.predict_url,
                {
                    "home_team": "Manchester United",
                    "away_team": "Arsenal",
                    "match_date": "2026-03-15",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error"], "not_found")
        self.assertIn("does not exist", payload["message"])
        self.assertNotIn("traceback", str(payload).lower())

    def test_admin_active_model_requires_token(self):
        ModelVersion.objects.create(version="v-test", artifact_path="models/model_latest.joblib", is_active=True)
        user = get_user_model().objects.create_user(username="apiadmin", password="secret-pass")
        token = Token.objects.create(user=user)

        auth_response = self.client.get(
            self.admin_active_model_url,
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )
        self.assertEqual(auth_response.status_code, 200, auth_response.content)

        response = self.client.get(self.admin_active_model_url)
        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertEqual(payload["error"], "forbidden")
        self.assertIn("token", payload["message"].lower())

    @patch("matches.views._metadata_file_exists", return_value=True)
    @patch("matches.views._active_artifact")
    def test_health_returns_ok_when_model_loaded(self, mock_active_artifact, mock_metadata_exists):
        mock_active_artifact.return_value = (
            {"paths": {}},
            Path("models/model_latest.joblib"),
            {"trained_at": "health-ok-v1", "feature_columns": ["home_points_5"]},
        )

        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["artifact_loaded"])
        self.assertEqual(payload["model_version"], "health-ok-v1")

    @patch("matches.views._active_artifact")
    def test_missing_model_health_and_insufficient_history_errors_are_structured(self, mock_active_artifact):
        mock_active_artifact.side_effect = FileNotFoundError("Active model artifact not found. Run training first.")
        health_response = self.client.get(self.health_url)

        self.assertEqual(health_response.status_code, 503)
        self.assertEqual(health_response.json()["status"], "error")
        self.assertEqual(health_response.json()["error"], "model_not_loaded")

        Team.objects.create(name="Manchester United")
        Team.objects.create(name="Arsenal")

        with patch("matches.views._active_artifact", return_value=_fake_artifact_bundle()), patch(
            "matches.views.read_or_build_matches", return_value=_history_df(match_count_per_team=1)
        ):
            response = self.client.post(
                self.predict_url,
                {
                    "home_team": "Manchester United",
                    "away_team": "Arsenal",
                    "match_date": "2026-03-15",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "insufficient_history")
        self.assertEqual(
            response.json()["message"],
            "Not enough historical matches to compute rolling features.",
        )
