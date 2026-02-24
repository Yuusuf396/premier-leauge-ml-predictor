from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from matches.models import Team
from src.data import read_or_build_matches, read_raw_matches


def _resolve_config() -> dict:
    config_path = Path(settings.ML_CONFIG_PATH)
    try:
        from src.utils import load_config

        config = load_config(config_path)
    except ModuleNotFoundError as exc:
        if exc.name != "yaml":
            raise
        config = {
            "paths": {
                "raw_glob": "premier-league-api/data/raw/seasons/*.csv",
                "processed_matches": "data/processed/matches_clean.parquet",
                "features_table": "data/processed/features_table.parquet",
                "model_dir": "models",
                "report_dir": "reports",
                "run_log": "reports/run_history.txt",
            },
            "training": {"use_cached_processed": True},
        }
    config_root = config_path.parent
    for key in ["model_dir", "raw_glob", "processed_matches", "features_table", "report_dir", "run_log"]:
        path_value = config["paths"].get(key)
        if not path_value:
            continue
        p = Path(path_value)
        if not p.is_absolute():
            config["paths"][key] = str(config_root / p)
    return config


class Command(BaseCommand):
    help = "Create missing Team rows from historical/parquet data without deleting any existing teams."

    def handle(self, *args, **options):
        config = _resolve_config()
        try:
            matches = read_or_build_matches(config)
        except ImportError:
            self.stdout.write("Parquet engine unavailable; falling back to raw CSV history.")
            matches = read_raw_matches(config["paths"]["raw_glob"])

        names = sorted(set(matches["home_team"].dropna().tolist()) | set(matches["away_team"].dropna().tolist()))
        created_count = 0
        existing_count = 0

        for name in names:
            _, created = Team.objects.get_or_create(name=str(name).strip())
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(self.style.SUCCESS("Team sync complete."))
        self.stdout.write(f"created_count={created_count}")
        self.stdout.write(f"existing_count={existing_count}")
