from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def season_start_year(season_label: str) -> int:
    # Example: "2016-17" -> 2016
    return int(str(season_label).split("-")[0])


def sort_seasons(seasons: list[str]) -> list[str]:
    return sorted(seasons, key=season_start_year)


def json_dump(obj: Any, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def dataframe_hash(df) -> str:
    """Stable-ish hash used for run traceability."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def append_run_log(path: str | Path, event: str, payload: dict[str, Any]) -> None:
    """Append one line of run metadata for auditability and accuracy tracking."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [f"ts={ts}", f"event={event}"]
    for key in sorted(payload):
        value = payload[key]
        if isinstance(value, float):
            parts.append(f"{key}={value:.6f}")
        else:
            parts.append(f"{key}={value}")

    with open(out_path, "a", encoding="utf-8") as f:
        f.write(" | ".join(parts) + "\n")
