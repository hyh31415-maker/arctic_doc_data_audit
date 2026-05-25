from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..manifest import read_manifest
from ..normalize import canonical_river, clean_text, coordinates_for_river, parse_date, station_for_river, to_numeric, version_from_text
from ..paths import PROCESSED_DIR, path, relpath
from ..schemas import ensure_columns, write_table
from .doc_labels import _find_workbooks, _first_col, _header_row, _cell


ABS_BANDS = ["A254", "A350", "A355", "A375", "A412", "A420", "A440"]
TARGET_WAVELENGTHS = {254, 350, 355, 375, 412, 420, 440}
RIVER_SHEETS = {"Ob", "Yenisey", "Lena", "Kolyma", "Yukon", "Mackenzie"}


def _optical_id(*parts: Any) -> str:
    text = "|".join(clean_text(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    n = to_numeric(numerator)
    d = to_numeric(denominator)
    if n is None or d in (None, 0):
        return None
    return n / d


def _slope(row: pd.Series, low: int, high: int) -> float | None:
    wavelengths: list[float] = []
    values: list[float] = []
    for column in ABS_BANDS:
        wavelength = int(column[1:])
        value = to_numeric(row.get(column))
        if low <= wavelength <= high and value is not None and value > 0:
            wavelengths.append(float(wavelength))
            values.append(float(value))
    if len(values) < 2:
        return None
    fit = np.polyfit(np.array(wavelengths), np.log(np.array(values)), 1)
    return float(-fit[0])


def _latest_version(source_id: str) -> str:
    manifest = read_manifest()
    if manifest.empty:
        return ""
    rows = manifest[(manifest["source_id"] == source_id) & (manifest["version_detected"].astype(str) != "")]
    return rows.iloc[-1]["version_detected"] if not rows.empty else ""


def _parse_water_quality_absorbance(workbook: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(workbook)
    rows: list[dict[str, Any]] = []
    version = ""
    for sheet in xls.sheet_names:
        if sheet not in RIVER_SHEETS:
            continue
        raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        header_idx = _header_row(raw)
        if header_idx is None:
            continue
        if not version:
            version = version_from_text(*raw.iloc[:5, :3].to_numpy().ravel(), workbook.name)
        headers = raw.iloc[header_idx].tolist()
        units = raw.iloc[header_idx + 1].tolist()
        date_col = _first_col(headers, units, "Date")
        river_col = _first_col(headers, units, "River")
        id_col = _first_col(headers, units, "ID")
        doc_col = _first_col(headers, units, "DOC")
        flag_cols = {band: _first_col(headers, units, band, flag=True) for band in ABS_BANDS}
        value_cols = {band: _first_col(headers, units, band, flag=False) for band in ABS_BANDS}
        river = canonical_river(sheet)
        station = station_for_river(river)
        for row_idx in range(header_idx + 2, len(raw)):
            record = raw.iloc[row_idx]
            date = parse_date(_cell(record, date_col))
            if pd.isna(date):
                continue
            values = {band: to_numeric(_cell(record, col)) if col is not None else None for band, col in value_cols.items()}
            if not any(value is not None for value in values.values()):
                continue
            flags = [clean_text(_cell(record, col)).upper() for col in flag_cols.values() if col is not None and clean_text(_cell(record, col))]
            row = {
                "optical_lab_id": _optical_id("arcticgro_water_quality_current", workbook, sheet, row_idx + 1),
                "source_id": "arcticgro_water_quality_current",
                "dataset_version": version,
                "river": canonical_river(_cell(record, river_col)) if river_col is not None else river,
                "station": station,
                "date": date.date().isoformat(),
                "sample_id": clean_text(_cell(record, id_col)),
                **values,
                "SUVA254": _safe_ratio(values.get("A254"), _cell(record, doc_col)),
                "spectral_slope_275_295": None,
                "spectral_slope_350_400": None,
                "units": "absorbance units; SUVA254 computed as A254/DOC_mgC_L when DOC is available",
                "method": "ArcticGRO Water Quality Axxx columns",
                "quality_flag": ";".join(sorted(set(flags))),
                "can_be_daily_predictor": False,
                "can_be_optical_validation": True,
                "notes": f"source_file={relpath(workbook)}; source_sheet={sheet}; source_row={row_idx + 1}",
            }
            rows.append(row)
    return pd.DataFrame(rows)


def _parse_absorbance_workbook(workbook: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(workbook)
    rows: list[dict[str, Any]] = []
    version = ""
    for sheet in xls.sheet_names:
        if sheet not in RIVER_SHEETS:
            continue
        raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        if not version:
            version = version_from_text(*raw.iloc[:5, :3].to_numpy().ravel(), workbook.name)
        header_rows = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower() == "wavelength"].tolist()
        if not header_rows:
            continue
        header_idx = int(header_rows[0])
        dates = [parse_date(value) for value in raw.iloc[header_idx, 1:].tolist()]
        body = raw.iloc[header_idx + 1 :].copy()
        wavelengths = pd.to_numeric(body.iloc[:, 0], errors="coerce")
        for col_offset, date in enumerate(dates, start=1):
            if pd.isna(date):
                continue
            values: dict[str, float | None] = {band: None for band in ABS_BANDS}
            for row_position, wavelength in wavelengths.items():
                if pd.isna(wavelength):
                    continue
                rounded = int(round(float(wavelength)))
                if rounded in TARGET_WAVELENGTHS:
                    values[f"A{rounded}"] = to_numeric(body.loc[row_position, col_offset])
            if not any(value is not None for value in values.values()):
                continue
            temp = pd.Series(values)
            rows.append(
                {
                    "optical_lab_id": _optical_id("arcticgro_absorbance_current", workbook, sheet, date),
                    "source_id": "arcticgro_absorbance_current",
                    "dataset_version": version,
                    "river": canonical_river(sheet),
                    "station": station_for_river(canonical_river(sheet)),
                    "date": date.date().isoformat(),
                    "sample_id": "",
                    **values,
                    "SUVA254": None,
                    "spectral_slope_275_295": _slope(temp, 275, 295),
                    "spectral_slope_350_400": _slope(temp, 350, 400),
                    "units": "absorbance units",
                    "method": "ArcticGRO Absorbance full-spectrum workbook",
                    "quality_flag": "",
                    "can_be_daily_predictor": False,
                    "can_be_optical_validation": True,
                    "notes": f"source_file={relpath(workbook)}; source_sheet={sheet}; matrix_date_column={col_offset + 1}",
                }
            )
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for workbook in _find_workbooks("arcticgro_water_quality_current", "data/raw/arcticgro/water_quality/*.xlsx"):
        frames.append(_parse_water_quality_absorbance(workbook))
    for workbook in _find_workbooks("arcticgro_absorbance_current", "data/raw/arcticgro/absorbance/*.xlsx"):
        frames.append(_parse_absorbance_workbook(workbook))
    frames = [frame.dropna(axis=1, how="all") for frame in frames if not frame.empty]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    frame = ensure_columns(frame, "lab_optical_proxy_canonical")
    if not frame.empty:
        for column in ["can_be_daily_predictor", "can_be_optical_validation"]:
            frame[column] = frame[column].astype(bool)
        frame["can_be_daily_predictor"] = False
    write_table(frame, "lab_optical_proxy_canonical", PROCESSED_DIR / "lab_optical_proxy_canonical.csv")
    return frame
