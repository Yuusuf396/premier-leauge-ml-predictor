from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
ODDS_TRIPLES = [
    ("B365H", "B365D", "B365A"),
    ("PSH", "PSD", "PSA"),
    ("WHH", "WHD", "WHA"),
    ("AvgH", "AvgD", "AvgA"),
]


TEAM_NAME_MAP = {
    "Nott'm Forest": "Nottingham Forest",
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Spurs": "Tottenham",
    "Wolves": "Wolverhampton Wanderers",
    "Newcastle": "Newcastle United",
    "Leicester": "Leicester City",
}


def _parse_dates(raw_dates: pd.Series) -> pd.Series:
    # First pass handles most football-data formats (dd/mm/yyyy).
    dt = pd.to_datetime(raw_dates, dayfirst=True, errors="coerce")

    # Fallback pass for any remaining values in uncommon formats.
    bad = dt.isna() & raw_dates.notna()
    if bad.any():
        fallback = pd.to_datetime(raw_dates[bad], errors="coerce")
        dt.loc[bad] = fallback
    return dt


def _derive_season_from_path(path: Path) -> str:
    m = re.search(r"(\d{4}-\d{2})", path.name)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot derive season label from filename: {path.name}")


def _normalize_team(name: str) -> str:
    clean = str(name).strip()
    return TEAM_NAME_MAP.get(clean, clean)


def _extract_odds(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["odds_home"] = np.nan
    out["odds_draw"] = np.nan
    out["odds_away"] = np.nan

    for h_col, d_col, a_col in ODDS_TRIPLES:
        if {h_col, d_col, a_col}.issubset(out.columns):
            out["odds_home"] = pd.to_numeric(out[h_col], errors="coerce")
            out["odds_draw"] = pd.to_numeric(out[d_col], errors="coerce")
            out["odds_away"] = pd.to_numeric(out[a_col], errors="coerce")
            break

    return out


def _infer_ftr(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if away_goals > home_goals:
        return "A"
    return "D"


def read_raw_matches(raw_glob: str) -> pd.DataFrame:
    if Path(raw_glob).is_absolute():
        files = [Path(p) for p in sorted(glob.glob(raw_glob))]
    else:
        files = sorted(Path().glob(raw_glob))
    if not files:
        raise FileNotFoundError(f"No files found for pattern: {raw_glob}")

    season_frames: list[pd.DataFrame] = []

    for file_path in files:
        season = _derive_season_from_path(file_path)
        raw = pd.read_csv(file_path, encoding="utf-8-sig")

        missing = REQUIRED_COLUMNS - set(raw.columns)
        if missing:
            raise ValueError(f"{file_path.name} missing required columns: {sorted(missing)}")

        base_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
        optional = ["FTR", "Time"]
        base_cols += [c for c in optional if c in raw.columns]

        work = _extract_odds(raw.copy())
        work = work.loc[:, base_cols + ["odds_home", "odds_draw", "odds_away"]].copy()

        work = work.rename(
            columns={
                "Date": "match_date",
                "Time": "kickoff_time",
                "HomeTeam": "home_team",
                "AwayTeam": "away_team",
                "FTHG": "home_goals",
                "FTAG": "away_goals",
                "FTR": "ftr",
            }
        )

        if "kickoff_time" not in work.columns:
            work["kickoff_time"] = "00:00"

        work["match_date"] = _parse_dates(work["match_date"])
        work["home_team"] = work["home_team"].map(_normalize_team)
        work["away_team"] = work["away_team"].map(_normalize_team)
        work["home_goals"] = pd.to_numeric(work["home_goals"], errors="coerce")
        work["away_goals"] = pd.to_numeric(work["away_goals"], errors="coerce")

        if "ftr" not in work.columns:
            work["ftr"] = np.nan

        work = work.dropna(subset=["match_date", "home_team", "away_team", "home_goals", "away_goals"])
        work = work[work["home_team"] != work["away_team"]]

        work["home_goals"] = work["home_goals"].astype(int)
        work["away_goals"] = work["away_goals"].astype(int)
        work["ftr"] = work["ftr"].where(work["ftr"].isin(["H", "D", "A"]))
        work["ftr"] = work.apply(
            lambda r: _infer_ftr(int(r["home_goals"]), int(r["away_goals"])) if pd.isna(r["ftr"]) else r["ftr"],
            axis=1,
        )

        work["season"] = season
        work["match_datetime"] = pd.to_datetime(
            work["match_date"].dt.strftime("%Y-%m-%d") + " " + work["kickoff_time"].fillna("00:00"),
            errors="coerce",
        )
        work["match_datetime"] = work["match_datetime"].fillna(work["match_date"])

        season_frames.append(work)

    matches = pd.concat(season_frames, ignore_index=True)
    matches = matches.sort_values(["match_datetime", "home_team", "away_team"]).reset_index(drop=True)

    # Drop exact duplicated fixtures inside same season/date/team pair.
    before = len(matches)
    matches = matches.drop_duplicates(subset=["season", "match_date", "home_team", "away_team"])
    dropped = before - len(matches)
    if dropped:
        print(f"Dropped {dropped} duplicate rows.")

    matches["match_id"] = np.arange(1, len(matches) + 1)

    return matches[
        [
            "match_id",
            "season",
            "match_date",
            "match_datetime",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
            "ftr",
            "odds_home",
            "odds_draw",
            "odds_away",
        ]
    ].copy()


def save_processed_matches(matches: pd.DataFrame, out_path: str) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    matches.to_parquet(p, index=False)


def read_or_build_matches(config: dict) -> pd.DataFrame:
    processed_path = Path(config["paths"]["processed_matches"])
    if processed_path.exists() and config.get("training", {}).get("use_cached_processed", True):
        return pd.read_parquet(processed_path)

    matches = read_raw_matches(config["paths"]["raw_glob"])
    save_processed_matches(matches, str(processed_path))
    return matches


def read_fixtures_csv(fixtures_path: str) -> pd.DataFrame:
    raw = pd.read_csv(fixtures_path, encoding="utf-8-sig")
    required = {"Date", "HomeTeam", "AwayTeam"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Fixtures file missing required columns: {sorted(missing)}")

    work = raw.copy()
    work = _extract_odds(work)
    work = work.rename(columns={"Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team"})
    work["match_date"] = _parse_dates(work["match_date"])
    work["home_team"] = work["home_team"].map(_normalize_team)
    work["away_team"] = work["away_team"].map(_normalize_team)
    work = work.dropna(subset=["match_date", "home_team", "away_team"])
    work = work[work["home_team"] != work["away_team"]]

    return work[["match_date", "home_team", "away_team", "odds_home", "odds_draw", "odds_away"]].copy()
