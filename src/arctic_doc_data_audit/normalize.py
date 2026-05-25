from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .paths import CONFIG_DIR


MISSING_TOKENS = {"", "na", "nan", "nc", "not collected", "not available", "bd", "dv", "none", "null"}


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def normalize_key(value: Any) -> str:
    return "".join(ch for ch in clean_text(value).lower() if ch.isalnum())


def load_rivers() -> dict[str, Any]:
    with (CONFIG_DIR / "rivers.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["rivers"]


def river_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, meta in load_rivers().items():
        lookup[normalize_key(canonical)] = canonical
        lookup[normalize_key(meta.get("canonical_name", canonical))] = canonical
        for alias in meta.get("aliases", []) or []:
            lookup[normalize_key(alias)] = canonical
    lookup.update({"ob": "Ob", "yenisei": "Yenisey", "yenisey": "Yenisey"})
    return lookup


def canonical_river(value: Any) -> str:
    key = normalize_key(value)
    return river_lookup().get(key, clean_text(value))


def station_for_river(river: str) -> str:
    meta = load_rivers().get(river, {})
    stations = meta.get("arcticgro_station_names") or []
    return stations[0] if stations else ""


def discharge_station_for_river(river: str) -> str:
    meta = load_rivers().get(river, {})
    stations = meta.get("discharge_station_names") or []
    return stations[0] if stations else station_for_river(river)


def coordinates_for_river(river: str) -> tuple[float | None, float | None]:
    meta = load_rivers().get(river, {})
    return meta.get("approximate_station_latitude"), meta.get("approximate_station_longitude")


def parse_date(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None:
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def version_from_text(*values: Any) -> str:
    text = " ".join(clean_text(value) for value in values)
    match = re.search(r"(20\d{6})", text)
    return match.group(1) if match else ""


def parameter_canonical(raw_parameter: Any) -> str:
    text = clean_text(raw_parameter).lower()
    compact = normalize_key(text)
    if compact in {"doc", "dissolvedorganiccarbon"} or "dissolved organic carbon" in text:
        return "DOC"
    if compact in {"toc", "totalorganiccarbon"} or "total organic carbon" in text:
        return "TOC"
    if compact in {"organiccarbon"} or text == "organic carbon":
        return "Organic carbon"
    return clean_text(raw_parameter)


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if clean_text(value).lower() in MISSING_TOKENS:
        return True
    return False


def to_numeric(value: Any) -> float | None:
    if is_missing_value(value):
        return None
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def convert_doc_to_mgC_L(value: Any, unit: Any) -> tuple[float | None, str]:
    numeric = to_numeric(value)
    unit_text = clean_text(unit)
    unit_key = normalize_key(unit_text.replace("µ", "u"))
    if numeric is None:
        return None, "missing_or_non_numeric_value"
    if unit_key in {"mgl", "mgcl", "mglasc", "mgcasl"}:
        return numeric, ""
    if unit_key in {"ugl", "ugcl", "uglasc", "ugcasl"}:
        return numeric / 1000.0, ""
    return None, f"invalid_or_unsupported_unit:{unit_text}"


def read_excel_headerless(path: str | Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, header=None)


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_text(value).lower() in {"true", "1", "yes", "y"}


def day_of_year(timestamp: pd.Timestamp) -> int | float:
    if pd.isna(timestamp):
        return np.nan
    return int(timestamp.dayofyear)

