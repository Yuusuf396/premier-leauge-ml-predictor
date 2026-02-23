from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "home_points_5",
    "home_points_10",
    "away_points_5",
    "away_points_10",
    "home_goal_diff_5",
    "home_goal_diff_10",
    "away_goal_diff_5",
    "away_goal_diff_10",
    "home_goals_for_5",
    "away_goals_for_5",
    "home_goals_against_5",
    "away_goals_against_5",
    "home_home_points_5",
    "away_away_points_5",
    "home_rest_days",
    "away_rest_days",
    "rest_days_diff",
    "elo_home",
    "elo_away",
    "elo_diff",
    "implied_home",
    "implied_draw",
    "implied_away",
    "implied_edge_home_minus_away",
]


@dataclass
class TeamState:
    elo: float
    last_date: pd.Timestamp | None = None
    all_matches: deque = field(default_factory=lambda: deque(maxlen=40))
    home_matches: deque = field(default_factory=lambda: deque(maxlen=20))
    away_matches: deque = field(default_factory=lambda: deque(maxlen=20))


def _points_from_result(result: str, perspective: str) -> int:
    if result == "D":
        return 1
    if result == "H":
        return 3 if perspective == "home" else 0
    if result == "A":
        return 0 if perspective == "home" else 3
    raise ValueError(f"Unexpected result label: {result}")


def _rolling_avg(history: deque, field_name: str, window: int, prior: float) -> float:
    if not history:
        return prior
    items = list(history)[-window:]
    values = [x[field_name] for x in items]
    if not values:
        return prior
    return float(np.mean(values))


def _normalized_implied_probabilities(odds_home: float, odds_draw: float, odds_away: float) -> tuple[float, float, float]:
    if np.any(np.isnan([odds_home, odds_draw, odds_away])):
        return np.nan, np.nan, np.nan
    if odds_home <= 1.0 or odds_draw <= 1.0 or odds_away <= 1.0:
        return np.nan, np.nan, np.nan

    inv = np.array([1.0 / odds_home, 1.0 / odds_draw, 1.0 / odds_away], dtype=float)
    total = inv.sum()
    if total <= 0:
        return np.nan, np.nan, np.nan
    probs = inv / total
    return float(probs[0]), float(probs[1]), float(probs[2])


def _assert_past_only(state: TeamState, current_date: pd.Timestamp, team_name: str) -> None:
    # Leakage guard: no stored history date may be current/future relative to feature row.
    for item in state.all_matches:
        if item["match_date"] >= current_date:
            raise AssertionError(
                f"Leakage detected for team={team_name}: history date {item['match_date']} >= current {current_date}"
            )


def _ensure_team_state(states: dict[str, TeamState], team: str, init_elo: float) -> TeamState:
    if team not in states:
        states[team] = TeamState(elo=init_elo)
    return states[team]


def _update_states_after_match(
    home_state: TeamState,
    away_state: TeamState,
    home_team: str,
    away_team: str,
    match_date: pd.Timestamp,
    home_goals: int,
    away_goals: int,
    ftr: str,
    elo_k: float,
    elo_home_adv: float,
) -> None:
    home_points = _points_from_result(ftr, perspective="home")
    away_points = _points_from_result(ftr, perspective="away")

    home_entry = {
        "match_date": match_date,
        "points": home_points,
        "goals_for": float(home_goals),
        "goals_against": float(away_goals),
        "goal_diff": float(home_goals - away_goals),
        "is_home": 1.0,
        "team": home_team,
        "opponent": away_team,
    }
    away_entry = {
        "match_date": match_date,
        "points": away_points,
        "goals_for": float(away_goals),
        "goals_against": float(home_goals),
        "goal_diff": float(away_goals - home_goals),
        "is_home": 0.0,
        "team": away_team,
        "opponent": home_team,
    }

    home_state.all_matches.append(home_entry)
    away_state.all_matches.append(away_entry)
    home_state.home_matches.append(home_entry)
    away_state.away_matches.append(away_entry)
    home_state.last_date = match_date
    away_state.last_date = match_date

    # ELO update after feature row is created.
    adj_home_elo = home_state.elo + elo_home_adv
    expected_home = 1.0 / (1.0 + 10.0 ** ((away_state.elo - adj_home_elo) / 400.0))
    actual_home = 1.0 if ftr == "H" else (0.5 if ftr == "D" else 0.0)

    home_state.elo = home_state.elo + elo_k * (actual_home - expected_home)
    away_state.elo = away_state.elo + elo_k * ((1.0 - actual_home) - (1.0 - expected_home))


def build_features(matches_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build leakage-safe match features in strict chronological order.

    Every feature row for match t is computed from team state before match t updates are applied.
    """
    priors = config["features"]["priors"]
    elo_cfg = config["features"]["elo"]

    matches = matches_df.sort_values(["match_datetime", "home_team", "away_team"]).copy()
    states: dict[str, TeamState] = {}
    rows: list[dict[str, Any]] = []

    for row in matches.itertuples(index=False):
        match_date = pd.Timestamp(row.match_date)
        home_team = row.home_team
        away_team = row.away_team

        home_state = _ensure_team_state(states, home_team, init_elo=float(elo_cfg["initial_rating"]))
        away_state = _ensure_team_state(states, away_team, init_elo=float(elo_cfg["initial_rating"]))

        _assert_past_only(home_state, match_date, home_team)
        _assert_past_only(away_state, match_date, away_team)

        home_rest = (
            float((match_date - home_state.last_date).days)
            if home_state.last_date is not None
            else float(priors["rest_days"])
        )
        away_rest = (
            float((match_date - away_state.last_date).days)
            if away_state.last_date is not None
            else float(priors["rest_days"])
        )

        implied_home, implied_draw, implied_away = _normalized_implied_probabilities(
            float(row.odds_home) if pd.notna(row.odds_home) else np.nan,
            float(row.odds_draw) if pd.notna(row.odds_draw) else np.nan,
            float(row.odds_away) if pd.notna(row.odds_away) else np.nan,
        )

        feat = {
            "match_id": int(row.match_id),
            "season": row.season,
            "match_date": match_date,
            "home_team": home_team,
            "away_team": away_team,
            "ftr": row.ftr,
            "home_goals": int(row.home_goals),
            "away_goals": int(row.away_goals),
            "home_points_5": _rolling_avg(home_state.all_matches, "points", 5, float(priors["points"])),
            "home_points_10": _rolling_avg(home_state.all_matches, "points", 10, float(priors["points"])),
            "away_points_5": _rolling_avg(away_state.all_matches, "points", 5, float(priors["points"])),
            "away_points_10": _rolling_avg(away_state.all_matches, "points", 10, float(priors["points"])),
            "home_goal_diff_5": _rolling_avg(home_state.all_matches, "goal_diff", 5, float(priors["goal_diff"])),
            "home_goal_diff_10": _rolling_avg(home_state.all_matches, "goal_diff", 10, float(priors["goal_diff"])),
            "away_goal_diff_5": _rolling_avg(away_state.all_matches, "goal_diff", 5, float(priors["goal_diff"])),
            "away_goal_diff_10": _rolling_avg(away_state.all_matches, "goal_diff", 10, float(priors["goal_diff"])),
            "home_goals_for_5": _rolling_avg(home_state.all_matches, "goals_for", 5, float(priors["goals_for"])),
            "away_goals_for_5": _rolling_avg(away_state.all_matches, "goals_for", 5, float(priors["goals_for"])),
            "home_goals_against_5": _rolling_avg(home_state.all_matches, "goals_against", 5, float(priors["goals_against"])),
            "away_goals_against_5": _rolling_avg(away_state.all_matches, "goals_against", 5, float(priors["goals_against"])),
            "home_home_points_5": _rolling_avg(home_state.home_matches, "points", 5, float(priors["points"])),
            "away_away_points_5": _rolling_avg(away_state.away_matches, "points", 5, float(priors["points"])),
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "rest_days_diff": home_rest - away_rest,
            "elo_home": float(home_state.elo),
            "elo_away": float(away_state.elo),
            "elo_diff": float(home_state.elo - away_state.elo),
            "implied_home": implied_home,
            "implied_draw": implied_draw,
            "implied_away": implied_away,
            "implied_edge_home_minus_away": implied_home - implied_away if pd.notna(implied_home) and pd.notna(implied_away) else np.nan,
        }

        rows.append(feat)

        _update_states_after_match(
            home_state=home_state,
            away_state=away_state,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            home_goals=int(row.home_goals),
            away_goals=int(row.away_goals),
            ftr=row.ftr,
            elo_k=float(elo_cfg["k_factor"]),
            elo_home_adv=float(elo_cfg["home_advantage"]),
        )

    out = pd.DataFrame(rows)

    # Explicit leakage sanity checks.
    if not (out["match_date"].is_monotonic_increasing):
        raise AssertionError("Feature rows are not chronological.")

    return out


def _state_from_history(history_df: pd.DataFrame, config: dict[str, Any]) -> dict[str, TeamState]:
    elo_cfg = config["features"]["elo"]
    states: dict[str, TeamState] = {}

    ordered = history_df.sort_values(["match_datetime", "home_team", "away_team"])
    for row in ordered.itertuples(index=False):
        home_state = _ensure_team_state(states, row.home_team, float(elo_cfg["initial_rating"]))
        away_state = _ensure_team_state(states, row.away_team, float(elo_cfg["initial_rating"]))
        _update_states_after_match(
            home_state=home_state,
            away_state=away_state,
            home_team=row.home_team,
            away_team=row.away_team,
            match_date=pd.Timestamp(row.match_date),
            home_goals=int(row.home_goals),
            away_goals=int(row.away_goals),
            ftr=row.ftr,
            elo_k=float(elo_cfg["k_factor"]),
            elo_home_adv=float(elo_cfg["home_advantage"]),
        )

    return states


def build_fixture_features(history_df: pd.DataFrame, fixtures_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build inference-time features for upcoming fixtures from prior history only."""
    priors = config["features"]["priors"]
    states = _state_from_history(history_df, config)

    rows: list[dict[str, Any]] = []
    fixtures = fixtures_df.sort_values(["match_date", "home_team", "away_team"]).copy()

    for row in fixtures.itertuples(index=False):
        match_date = pd.Timestamp(row.match_date)
        home_state = states.get(row.home_team, TeamState(elo=float(config["features"]["elo"]["initial_rating"])))
        away_state = states.get(row.away_team, TeamState(elo=float(config["features"]["elo"]["initial_rating"])))

        home_rest = (
            float((match_date - home_state.last_date).days)
            if home_state.last_date is not None
            else float(priors["rest_days"])
        )
        away_rest = (
            float((match_date - away_state.last_date).days)
            if away_state.last_date is not None
            else float(priors["rest_days"])
        )

        implied_home, implied_draw, implied_away = _normalized_implied_probabilities(
            float(row.odds_home) if pd.notna(row.odds_home) else np.nan,
            float(row.odds_draw) if pd.notna(row.odds_draw) else np.nan,
            float(row.odds_away) if pd.notna(row.odds_away) else np.nan,
        )

        feat = {
            "match_date": match_date,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "home_points_5": _rolling_avg(home_state.all_matches, "points", 5, float(priors["points"])),
            "home_points_10": _rolling_avg(home_state.all_matches, "points", 10, float(priors["points"])),
            "away_points_5": _rolling_avg(away_state.all_matches, "points", 5, float(priors["points"])),
            "away_points_10": _rolling_avg(away_state.all_matches, "points", 10, float(priors["points"])),
            "home_goal_diff_5": _rolling_avg(home_state.all_matches, "goal_diff", 5, float(priors["goal_diff"])),
            "home_goal_diff_10": _rolling_avg(home_state.all_matches, "goal_diff", 10, float(priors["goal_diff"])),
            "away_goal_diff_5": _rolling_avg(away_state.all_matches, "goal_diff", 5, float(priors["goal_diff"])),
            "away_goal_diff_10": _rolling_avg(away_state.all_matches, "goal_diff", 10, float(priors["goal_diff"])),
            "home_goals_for_5": _rolling_avg(home_state.all_matches, "goals_for", 5, float(priors["goals_for"])),
            "away_goals_for_5": _rolling_avg(away_state.all_matches, "goals_for", 5, float(priors["goals_for"])),
            "home_goals_against_5": _rolling_avg(home_state.all_matches, "goals_against", 5, float(priors["goals_against"])),
            "away_goals_against_5": _rolling_avg(away_state.all_matches, "goals_against", 5, float(priors["goals_against"])),
            "home_home_points_5": _rolling_avg(home_state.home_matches, "points", 5, float(priors["points"])),
            "away_away_points_5": _rolling_avg(away_state.away_matches, "points", 5, float(priors["points"])),
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "rest_days_diff": home_rest - away_rest,
            "elo_home": float(home_state.elo),
            "elo_away": float(away_state.elo),
            "elo_diff": float(home_state.elo - away_state.elo),
            "implied_home": implied_home,
            "implied_draw": implied_draw,
            "implied_away": implied_away,
            "implied_edge_home_minus_away": implied_home - implied_away if pd.notna(implied_home) and pd.notna(implied_away) else np.nan,
        }
        rows.append(feat)

    return pd.DataFrame(rows)
