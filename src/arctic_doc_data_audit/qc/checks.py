from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..paths import path
from ..preprocess.training_matrix import FORBIDDEN
from ..schemas import required_columns


def assert_required_columns(table_name: str, frame: pd.DataFrame) -> None:
    missing = [column for column in required_columns(table_name) if column not in frame.columns]
    if missing:
        raise AssertionError(f"{table_name} missing required columns: {missing}")


def assert_no_lab_optical_leakage(frame: pd.DataFrame) -> None:
    leaked = sorted(FORBIDDEN.intersection(frame.columns))
    if leaked:
        raise AssertionError(f"Lab optical columns leaked into training matrix: {leaked}")


def gitignore_excludes_raw(project: Path | None = None) -> bool:
    root = project or path()
    text = (root / ".gitignore").read_text(encoding="utf-8")
    required = ["data/raw/", "data/raw_external/", "data/interim/", "data/processed/"]
    return all(item in text for item in required)

