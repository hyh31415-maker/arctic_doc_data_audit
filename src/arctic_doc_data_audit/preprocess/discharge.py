from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..manifest import read_manifest
from ..normalize import clean_text, discharge_station_for_river, parse_date, version_from_text
from ..paths import PROCESSED_DIR, path, relpath
from ..schemas import ensure_columns, write_table


def _discharge_workbooks() -> list[Path]:
    manifest = read_manifest()
    if not manifest.empty:
        rows = manifest[(manifest["source_id"] == "arcticgro_discharge_current") & (manifest["download_status"] == "downloaded")]
        paths = [path(value) for value in rows["local_path"].tolist() if str(value).endswith(".xlsx")]
        paths = [value for value in paths if value.exists()]
        if paths:
            return sorted(paths)
    return sorted(path().glob("data/raw/arcticgro/discharge/*_Version_*.xlsx"))


def parse_discharge_workbook(workbook: Path) -> pd.DataFrame:
    raw = pd.read_excel(workbook)
    lower = {clean_text(column).lower(): column for column in raw.columns}
    river_col = lower.get("river")
    station_col = lower.get("station_name") or lower.get("station")
    date_col = lower.get("date")
    discharge_col = lower.get("discharge") or lower.get("q")
    flag_col = lower.get("flag")
    rows: list[dict[str, Any]] = []
    version = version_from_text(workbook.name)
    if not river_col or not date_col or not discharge_col:
        return pd.DataFrame()
    for _, row in raw.iterrows():
        date = parse_date(row.get(date_col))
        if pd.isna(date):
            continue
        original = row.get(discharge_col)
        q = pd.to_numeric(pd.Series([original]), errors="coerce").iloc[0]
        river = clean_text(row.get(river_col))
        station = clean_text(row.get(station_col)) if station_col else ""
        rows.append(
            {
                "river": river,
                "station": station if station and station.upper() != "NA" else discharge_station_for_river(river),
                "date": date.date().isoformat(),
                "Q_m3s": float(q) if pd.notna(q) else pd.NA,
                "source_id": "arcticgro_discharge_current",
                "dataset_version": version,
                "original_value": original,
                "original_unit": "m3/s",
                "quality_flag": clean_text(row.get(flag_col)).upper() if flag_col else "",
                "provenance_tier": "official_current",
                "notes": f"source_file={relpath(workbook)}",
            }
        )
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    frames = [parse_discharge_workbook(workbook) for workbook in _discharge_workbooks()]
    frame = pd.concat([item for item in frames if not item.empty], ignore_index=True) if frames else pd.DataFrame()
    frame = ensure_columns(frame, "daily_discharge_canonical")
    if not frame.empty:
        frame = frame.drop_duplicates(subset=["river", "station", "date", "source_id"], keep="last")
        frame = frame.sort_values(["river", "date"]).reset_index(drop=True)
    write_table(frame, "daily_discharge_canonical", PROCESSED_DIR / "daily_discharge_canonical.csv")
    return frame

