from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .paths import CONFIG_DIR, PROCESSED_DIR, ensure_project_dirs


def load_schema_config() -> dict[str, Any]:
    with (CONFIG_DIR / "schema.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def required_columns(table_name: str) -> list[str]:
    config = load_schema_config()
    return list(config["tables"][table_name]["required_columns"])


def empty_table(table_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=required_columns(table_name))


def ensure_columns(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    frame = frame.copy()
    columns = required_columns(table_name)
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[columns + [col for col in frame.columns if col not in columns]]


def validate_columns(frame: pd.DataFrame, table_name: str) -> None:
    missing = [column for column in required_columns(table_name) if column not in frame.columns]
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


def write_table(frame: pd.DataFrame, table_name: str, out_path: str | Path | None = None) -> Path:
    ensure_project_dirs()
    frame = ensure_columns(frame, table_name)
    validate_columns(frame, table_name)
    destination = Path(out_path) if out_path else PROCESSED_DIR / f"{table_name}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    return destination


def read_table_if_exists(table_name: str, default_empty: bool = True) -> pd.DataFrame:
    candidate = PROCESSED_DIR / f"{table_name}.csv"
    if candidate.exists():
        return pd.read_csv(candidate)
    if default_empty:
        return empty_table(table_name)
    raise FileNotFoundError(candidate)

