from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..deduplicate import apply_deduplication
from ..manifest import read_manifest
from ..normalize import (
    canonical_river,
    clean_text,
    convert_doc_to_mgC_L,
    coordinates_for_river,
    day_of_year,
    discharge_station_for_river,
    parameter_canonical,
    parse_date,
    station_for_river,
    version_from_text,
)
from ..paths import PROCESSED_DIR, TABLE_DIR, path, relpath
from ..schemas import ensure_columns, write_table


BAD_FLAGS = {"DV", "NC", "NA"}
CAUTION_FLAGS = {"PV", "CAU", "BD", "CV"}
RIVER_SHEETS = {"Ob", "Yenisey", "Lena", "Kolyma", "Yukon", "Mackenzie"}
DOC_PARAMETERS = ["DOC", "TOC", "Organic carbon"]


def _latest_manifest_file(source_id: str) -> Path | None:
    manifest = read_manifest()
    if manifest.empty:
        return None
    rows = manifest[(manifest["source_id"] == source_id) & (manifest["download_status"] == "downloaded")]
    rows = rows[rows["local_path"].astype(str).str.endswith(".xlsx", na=False)]
    if rows.empty:
        return None
    rows = rows.sort_values("retrieved_at_utc")
    candidate = path(rows.iloc[-1]["local_path"])
    return candidate if candidate.exists() else None


def _find_workbooks(source_id: str, fallback_glob: str) -> list[Path]:
    latest = _latest_manifest_file(source_id)
    if latest:
        return [latest]
    return sorted(path().glob(fallback_glob))


def _header_row(raw: pd.DataFrame) -> int | None:
    for idx in raw.index:
        row_values = [clean_text(value) for value in raw.loc[idx].tolist()]
        if "Phase" in row_values and "Date" in row_values and "DOC" in row_values:
            return int(idx)
    return None


def _col_indices(headers: list[Any], units: list[Any], name: str, *, flag: bool = False) -> list[int]:
    out: list[int] = []
    for idx, header in enumerate(headers):
        if clean_text(header).lower() != name.lower():
            continue
        unit = clean_text(units[idx]).lower() if idx < len(units) else ""
        if flag and unit == "flag":
            out.append(idx)
        if not flag and unit != "flag":
            out.append(idx)
    return out


def _first_col(headers: list[Any], units: list[Any], name: str, *, flag: bool = False) -> int | None:
    values = _col_indices(headers, units, name, flag=flag)
    return values[0] if values else None


def _cell(row: pd.Series, idx: int | None) -> Any:
    if idx is None:
        return pd.NA
    try:
        return row.iloc[idx]
    except IndexError:
        return pd.NA


def _label_id(*parts: Any) -> str:
    text = "|".join(clean_text(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def parse_arcticgro_doc_raw(workbook_path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(workbook_path)
    rows: list[dict[str, Any]] = []
    dataset_version = ""
    for sheet in xls.sheet_names:
        if sheet not in RIVER_SHEETS:
            continue
        raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        header_idx = _header_row(raw)
        if header_idx is None:
            continue
        if not dataset_version:
            dataset_version = version_from_text(*raw.iloc[:5, :3].to_numpy().ravel(), workbook_path.name)
        headers = raw.iloc[header_idx].tolist()
        units = raw.iloc[header_idx + 1].tolist()
        date_col = _first_col(headers, units, "Date")
        river_col = _first_col(headers, units, "River")
        sample_col = _first_col(headers, units, "ID")
        river = canonical_river(sheet)
        station = station_for_river(river)
        latitude, longitude = coordinates_for_river(river)
        for parameter in DOC_PARAMETERS:
            value_col = _first_col(headers, units, parameter)
            if value_col is None:
                continue
            flag_col = _first_col(headers, units, parameter, flag=True)
            unit = clean_text(units[value_col]) if value_col < len(units) else ""
            for row_idx in range(header_idx + 2, len(raw)):
                source_row = row_idx + 1
                record = raw.iloc[row_idx]
                date_value = _cell(record, date_col)
                raw_value = _cell(record, value_col)
                if pd.isna(date_value) and pd.isna(raw_value):
                    continue
                rows.append(
                    {
                        "source_id": "arcticgro_water_quality_current",
                        "source_file": relpath(workbook_path),
                        "source_sheet": sheet,
                        "source_row": source_row,
                        "raw_river": _cell(record, river_col) if river_col is not None else sheet,
                        "raw_station": station,
                        "raw_date": date_value,
                        "raw_parameter": parameter,
                        "raw_value": raw_value,
                        "raw_unit": unit,
                        "raw_flag": _cell(record, flag_col),
                        "raw_method": "ArcticGRO Water Quality workbook",
                        "raw_medium": "water",
                        "raw_fraction": "dissolved" if parameter == "DOC" else ("total" if parameter == "TOC" else ""),
                        "raw_latitude": latitude,
                        "raw_longitude": longitude,
                        "raw_sample_id": _cell(record, sample_col),
                        "notes": f"dataset_version={dataset_version}; workbook_sheet={sheet}",
                    }
                )
    return ensure_columns(pd.DataFrame(rows), "doc_labels_raw")


def build_doc_labels_raw() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for workbook in _find_workbooks("arcticgro_water_quality_current", "data/raw/arcticgro/water_quality/*.xlsx"):
        frames.append(parse_arcticgro_doc_raw(workbook))
    if not frames:
        return ensure_columns(pd.DataFrame(), "doc_labels_raw")
    return ensure_columns(pd.concat(frames, ignore_index=True), "doc_labels_raw")


def _tier(source_id: str, parameter: str, flag: str, conversion_reason: str, latitude: Any, longitude: Any, excluded: bool) -> str:
    if excluded:
        return "D"
    if source_id == "arcticgro_water_quality_current" and parameter == "DOC" and flag in {"", "AV"} and not conversion_reason and pd.notna(latitude) and pd.notna(longitude):
        return "A"
    if parameter == "DOC" and flag not in BAD_FLAGS and not conversion_reason:
        return "B"
    return "C"


def canonicalize_doc_labels(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        parsed_date = parse_date(row.get("raw_date"))
        river = canonical_river(row.get("raw_river"))
        station = clean_text(row.get("raw_station")) or station_for_river(river)
        parameter = parameter_canonical(row.get("raw_parameter"))
        value, conversion_reason = convert_doc_to_mgC_L(row.get("raw_value"), row.get("raw_unit"))
        flag = clean_text(row.get("raw_flag")).upper()
        is_toc = parameter == "TOC"
        exclusion_reasons: list[str] = []
        if pd.isna(parsed_date):
            exclusion_reasons.append("missing_or_invalid_date")
        if not river:
            exclusion_reasons.append("missing_river")
        if not station:
            exclusion_reasons.append("missing_station")
        if value is None:
            exclusion_reasons.append(conversion_reason or "missing_value")
        if flag in BAD_FLAGS:
            exclusion_reasons.append(f"unusable_quality_flag:{flag}")
        if is_toc:
            exclusion_reasons.append("TOC_retained_separately_not_DOC")
        latitude = pd.to_numeric(pd.Series([row.get("raw_latitude")]), errors="coerce").iloc[0]
        longitude = pd.to_numeric(pd.Series([row.get("raw_longitude")]), errors="coerce").iloc[0]
        if pd.isna(latitude) or pd.isna(longitude):
            exclusion_reasons.append("missing_coordinates")
        version = version_from_text(row.get("notes"), row.get("source_file"))
        excluded = bool(exclusion_reasons)
        tier = _tier(row.get("source_id", ""), parameter, flag, conversion_reason, latitude, longitude, excluded)
        can_train_doc = parameter == "DOC" and not excluded
        rows.append(
            {
                "label_id": _label_id(row.get("source_id"), row.get("source_file"), row.get("source_sheet"), row.get("source_row"), parameter),
                "source_id": row.get("source_id"),
                "dataset_version": version,
                "river": river,
                "station": station,
                "date": parsed_date.date().isoformat() if pd.notna(parsed_date) else "",
                "year": int(parsed_date.year) if pd.notna(parsed_date) else np.nan,
                "doy": day_of_year(parsed_date),
                "latitude": latitude,
                "longitude": longitude,
                "parameter_canonical": parameter,
                "value_mgC_L": value,
                "original_value": row.get("raw_value"),
                "original_unit": row.get("raw_unit"),
                "sample_id": clean_text(row.get("raw_sample_id")),
                "method": row.get("raw_method"),
                "medium": row.get("raw_medium"),
                "fraction": row.get("raw_fraction"),
                "quality_flag": flag,
                "provenance_tier": "official_current" if row.get("source_id") == "arcticgro_water_quality_current" else "candidate",
                "usability_tier": tier,
                "can_train_doc_model": can_train_doc,
                "can_train_daily_flux_model": can_train_doc,
                "is_toc_not_doc": is_toc,
                "is_duplicate": False,
                "duplicate_group_id": "",
                "preferred_record": True,
                "exclusion_reason": ";".join(exclusion_reasons),
                "notes": f"source_file={row.get('source_file')}; source_sheet={row.get('source_sheet')}; source_row={row.get('source_row')}; retrieved_version={version}",
            }
        )
    canonical = ensure_columns(pd.DataFrame(rows), "doc_labels_canonical")
    canonical, decisions = apply_deduplication(canonical)
    if not canonical.empty:
        mask_nonpreferred = canonical["is_duplicate"].astype(bool) & ~canonical["preferred_record"].astype(bool)
        canonical.loc[mask_nonpreferred, "can_train_doc_model"] = False
        canonical.loc[mask_nonpreferred, "can_train_daily_flux_model"] = False
        existing = canonical.loc[mask_nonpreferred, "exclusion_reason"].fillna("").astype(str)
        canonical.loc[mask_nonpreferred, "exclusion_reason"] = existing.where(existing == "", existing + ";") + "duplicate_nonpreferred"
    return ensure_columns(canonical, "doc_labels_canonical"), decisions


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = build_doc_labels_raw()
    write_table(raw, "doc_labels_raw", PROCESSED_DIR / "doc_labels_raw.csv")
    canonical, decisions = canonicalize_doc_labels(raw)
    write_table(canonical, "doc_labels_canonical", PROCESSED_DIR / "doc_labels_canonical.csv")
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    decisions.to_csv(TABLE_DIR / "duplicate_decisions.csv", index=False, encoding="utf-8")
    return raw, canonical

