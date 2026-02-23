"""Ingest Premier League CSV seasons from football-data.co.uk.

Outputs:
- data/processed/matches_processed.parquet
- data/processed/matches_train.parquet
- data/processed/matches_validation.parquet
- data/processed/matches_holdout.parquet
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


RAW_PATH = Path("data/raw/seasons")
PROCESSED_PATH = Path("data/processed")
RAW_PATH.mkdir(parents=True, exist_ok=True)
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class SplitConfig:
    train: tuple[str, ...]
    validation: tuple[str, ...]
    holdout: tuple[str, ...]


# Train on older history, validate on 2023-24, hold out 2024-25.
SPLIT_CONFIG = SplitConfig(
    train=(
        "2016-17",
        "2017-18",
        "2018-19",
        "2019-20",
        "2020-21",
        "2021-22",
        "2022-23",
    ),
    validation=("2023-24",),
    holdout=("2024-25",),
)


def season_to_url(season: str) -> str:
    """Map season label like 2023-24 -> football-data.co.uk CSV URL."""
    start_year = season.split("-")[0][-2:]
    end_year = season.split("-")[1]
    code = f"{start_year}{end_year}"
    return f"https://www.football-data.co.uk/mmz4281/{code}/E0.csv"


def download_csv(season: str) -> Path:
    csv_path = RAW_PATH / f"{season}.csv"
    if csv_path.exists():
        return csv_path

    local_fallback = os.getenv("INGEST_LOCAL_CSV", "").strip()
    if local_fallback:
        fallback_path = Path(local_fallback)
        if fallback_path.exists():
            csv_path.write_bytes(fallback_path.read_bytes())
            print(f"Using local fallback CSV for {season}: {fallback_path}")
            return csv_path

    url = season_to_url(season)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    csv_path.write_bytes(response.content)
    print(f"Downloaded {season} from {url}")
    return csv_path


def normalize_team_names(name: str) -> str:
    replacements = {
        "Nott'm Forest": "Nottingham Forest",
        "Man United": "Manchester United",
        "Man City": "Manchester City",
        "Spurs": "Tottenham",
        "Wolves": "Wolverhampton Wanderers",
    }
    return replacements.get(name, name)


def derive_matchday(df: pd.DataFrame) -> pd.DataFrame:
    """Derive approximate matchday from fixture order.

    A new matchday starts when a team repeats in the current round.
    """
    df = df.sort_values(["match_datetime", "home_team", "away_team"]).copy()

    current_matchday = 1
    teams_seen_this_round: set[str] = set()
    matchdays: list[int] = []

    for row in df.itertuples(index=False):
        home_team = row.home_team
        away_team = row.away_team

        if home_team in teams_seen_this_round or away_team in teams_seen_this_round:
            current_matchday += 1
            teams_seen_this_round.clear()

        teams_seen_this_round.add(home_team)
        teams_seen_this_round.add(away_team)
        matchdays.append(current_matchday)

    df["matchday"] = matchdays
    return df


def load_season_df(season: str) -> pd.DataFrame:
    csv_path = download_csv(season)

    # utf-8-sig handles BOM-prefixed headers like "\ufeffDiv".
    raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    required_cols = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
    missing_cols = required_cols - set(raw.columns)
    if missing_cols:
        raise ValueError(f"{season} missing required columns: {sorted(missing_cols)}")

    # Keep required columns plus useful optional match stats for ML features.
    optional_cols = ["Time", "FTR", "HS", "AS", "HST", "AST"]
    selected_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"] + [
        col for col in optional_cols if col in raw.columns
    ]
    df = raw.loc[:, selected_cols].copy()

    rename_map = {
        "Date": "match_date",
        "HomeTeam": "home_team",
        "AwayTeam": "away_team",
        "FTHG": "home_goals",
        "FTAG": "away_goals",
        "Time": "kickoff_time",
        "FTR": "full_time_result",
        "HS": "home_shots",
        "AS": "away_shots",
        "HST": "home_shots_on_target",
        "AST": "away_shots_on_target",
    }
    df = df.rename(columns=rename_map)

    df["home_team"] = df["home_team"].astype(str).str.strip().map(normalize_team_names)
    df["away_team"] = df["away_team"].astype(str).str.strip().map(normalize_team_names)
    df["match_date"] = pd.to_datetime(df["match_date"], dayfirst=True, errors="coerce")
    if "kickoff_time" not in df.columns:
        df["kickoff_time"] = "00:00"
    df["kickoff_time"] = df["kickoff_time"].fillna("00:00")
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce")
    for stat_col in ["home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target"]:
        if stat_col in df.columns:
            df[stat_col] = pd.to_numeric(df[stat_col], errors="coerce")
    df["season"] = season

    before = len(df)
    df = df.dropna(subset=["match_date", "home_team", "away_team", "home_goals", "away_goals"])
    df = df[df["home_team"] != df["away_team"]]
    dropped = before - len(df)
    if dropped:
        print(f"{season}: dropped {dropped} invalid rows")

    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    if "full_time_result" not in df.columns:
        df["full_time_result"] = df.apply(
            lambda row: "H" if row["home_goals"] > row["away_goals"] else ("A" if row["away_goals"] > row["home_goals"] else "D"),
            axis=1,
        )
    df["status"] = "completed"
    df["match_datetime"] = pd.to_datetime(
        df["match_date"].dt.strftime("%Y-%m-%d") + " " + df["kickoff_time"],
        errors="coerce",
    )
    df["match_datetime"] = df["match_datetime"].fillna(df["match_date"])

    df = derive_matchday(df)
    return df


def build_dataset(seasons: Iterable[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for season in seasons:
        print(f"Processing {season}...")
        frames.append(load_season_df(season))

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["match_datetime", "home_team", "away_team"]).reset_index(drop=True)
    combined["source"] = "football-data.co.uk"
    combined["source_match_id"] = (
        combined["season"]
        + ":"
        + combined["match_date"].dt.strftime("%Y-%m-%d")
        + ":"
        + combined["home_team"]
        + ":"
        + combined["away_team"]
    )
    combined = combined.drop_duplicates(subset=["source_match_id"]).copy()

    for col in ["home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target"]:
        if col not in combined.columns:
            combined[col] = pd.NA

    # Keep only columns we want downstream.
    return combined.loc[
        :,
        [
            "season",
            "matchday",
            "match_date",
            "kickoff_time",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "full_time_result",
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "status",
            "source",
            "source_match_id",
        ],
    ]


def write_splits(matches_df: pd.DataFrame) -> None:
    train_df = matches_df[matches_df["season"].isin(SPLIT_CONFIG.train)]
    validation_df = matches_df[matches_df["season"].isin(SPLIT_CONFIG.validation)]
    holdout_df = matches_df[matches_df["season"].isin(SPLIT_CONFIG.holdout)]

    matches_df.to_parquet(PROCESSED_PATH / "matches_processed.parquet", index=False)
    train_df.to_parquet(PROCESSED_PATH / "matches_train.parquet", index=False)
    validation_df.to_parquet(PROCESSED_PATH / "matches_validation.parquet", index=False)
    holdout_df.to_parquet(PROCESSED_PATH / "matches_holdout.parquet", index=False)

    print(f"Processed matches: {len(matches_df)}")
    print(f"Train matches: {len(train_df)}")
    print(f"Validation matches: {len(validation_df)}")
    print(f"Holdout matches: {len(holdout_df)}")


def main() -> None:
    default_seasons = (
        "2016-17",
        "2017-18",
        "2018-19",
        "2019-20",
        "2020-21",
        "2021-22",
        "2022-23",
        "2023-24",
        "2024-25",
    )
    override = os.getenv("INGEST_SEASONS", "").strip()
    seasons = tuple(s.strip() for s in override.split(",") if s.strip()) if override else default_seasons
    matches_df = build_dataset(seasons)
    write_splits(matches_df)
    print("Done.")


if __name__ == "__main__":
    main()
