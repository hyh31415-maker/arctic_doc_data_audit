from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..manifest import read_manifest, sha256_file
from ..normalize import canonical_river, clean_text, version_from_text
from ..paths import PROCESSED_DIR, RAW_EXTERNAL_DIR, TABLE_DIR, path, relpath
from ..schemas import ensure_columns, write_table


SOURCE_ID = "old_arctic_doc_snowmelt_untrained_data"
SNAPSHOT_ROOT = RAW_EXTERNAL_DIR / "old_project_snapshot"
QUALITY_HYDRO = "legacy_snapshot_needs_reproducibility_audit"
QUALITY_OPTICAL = "legacy_snapshot_optical_proxy_needs_audit"
QUALITY_ROI = "legacy_snapshot_requires_visual_audit"
QUALITY_AUX = "legacy_snapshot_context_needs_audit"
MODEL_TOKENS = ("model", "prediction", "flux", "joblib", "pkl")

INVENTORY_COLUMNS = [
    "snapshot_path",
    "original_relative_path",
    "file_name",
    "file_extension",
    "sha256",
    "file_size_bytes",
    "old_project_subdir",
    "inferred_river",
    "inferred_product_family",
    "inferred_stage",
    "row_count",
    "date_min",
    "date_max",
    "columns_json",
    "schema_fingerprint",
    "promotable_to_canonical",
    "target_canonical_table",
    "not_promoted_reason",
]


ROI_SET_BY_NAME = {
    "final_primary_roi.geojson": "final_primary",
    "final_strict_roi.geojson": "final_strict",
    "final_relaxed_roi.geojson": "final_relaxed",
    "auto_roi_center_channel.geojson": "auto_jrc_center_channel",
    "initial_roi_buffer.geojson": "initial_buffer",
    "station_point.geojson": "station_point",
}


HYDRO_COLUMN_MAP = {
    "temp2m_mean_k": "temperature_2m_C",
    "temp2m_mean_c": "temperature_2m_C",
    "temperature_2m_c": "temperature_2m_C",
    "precip_total_m": "precipitation_m",
    "precipitation_m": "precipitation_m",
    "snow_depth_mean_m": "snow_depth_m",
    "snow_depth_m": "snow_depth_m",
    "snowmelt_total_m": "snowmelt_m",
    "snowmelt_m": "snowmelt_m",
    "surface_runoff_total_m": "surface_runoff_m",
    "surface_runoff_m": "surface_runoff_m",
    "subsurface_runoff_total_m": "subsurface_runoff_m",
    "subsurface_runoff_m": "subsurface_runoff_m",
    "total_runoff_total_m": "total_runoff_m",
    "total_runoff_m": "total_runoff_m",
    "positive_degree_day_cday": "positive_degree_day_Cday",
    "pdd_cday": "positive_degree_day_Cday",
    "snow_cover_fraction": "snow_cover_fraction",
    "snow_depletion_rate_7d": "snow_depletion_rate_7d",
}

HYDRO_QC_SIDECAR_COLUMNS = {"mean_ndsi_snow_cover", "valid_modis_pixels"}


OPTICAL_COLUMN_MAP = {
    "blue_median": "blue",
    "green_median": "green",
    "red_median": "red",
    "nir_median": "nir",
    "swir1_median": "swir1",
    "swir2_median": "swir2",
    "blue_mean": "blue",
    "green_mean": "green",
    "red_mean": "red",
    "nir_mean": "nir",
    "swir1_mean": "swir1",
    "swir2_mean": "swir2",
}


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", clean_text(value).lower()).strip("_")


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _snapshot_manifest() -> pd.DataFrame:
    manifest = read_manifest()
    if manifest.empty:
        return pd.DataFrame()
    rows = manifest[
        (manifest["source_id"] == SOURCE_ID)
        & (manifest["download_status"].astype(str).str.lower() == "downloaded")
    ].copy()
    rows["snapshot_path"] = rows["local_path"]
    rows["original_relative_path"] = rows["local_path"].map(_original_relative_path)
    return rows


def _original_relative_path(local_path: Any) -> str:
    text = str(local_path).replace("\\", "/")
    marker = "data/raw_external/old_project_snapshot/"
    if marker in text:
        return text.split(marker, 1)[1]
    try:
        return Path(text).resolve().relative_to(SNAPSHOT_ROOT.resolve()).as_posix()
    except Exception:
        return text


def _old_project_subdir(original_relative_path: str) -> str:
    parts = original_relative_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "data":
        return "/".join(parts[:2])
    return ""


def _stage(original_relative_path: str) -> str:
    subdir = _old_project_subdir(original_relative_path)
    return {"data/raw": "raw", "data/raw_external": "raw_external", "data/interim": "interim"}.get(subdir, "")


def _infer_river_from_path(original_relative_path: str) -> str:
    parts = original_relative_path.replace("\\", "/").split("/")
    lower = [part.lower() for part in parts]
    if "by_river" in lower:
        idx = lower.index("by_river")
        if idx + 1 < len(parts):
            return canonical_river(parts[idx + 1])
    for part in parts:
        candidate = canonical_river(part)
        if candidate in {"Ob", "Yenisey", "Lena", "Kolyma", "Yukon", "Mackenzie"}:
            return candidate
    return ""


def _read_geojson_properties(file_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        features = data.get("features") or []
        if features:
            return dict(features[0].get("properties") or {})
        return dict(data.get("properties") or {})
    except Exception:
        return {}


def _infer_river(file_path: Path, original_relative_path: str) -> str:
    river = _infer_river_from_path(original_relative_path)
    if river:
        return river
    if file_path.suffix.lower() == ".geojson":
        props = _read_geojson_properties(file_path)
        return canonical_river(props.get("river", ""))
    return ""


def infer_product_family(original_relative_path: str, file_name: str) -> str:
    name = file_name.lower()
    text = original_relative_path.lower().replace("\\", "/")
    if any(token in name for token in MODEL_TOKENS):
        return "excluded_model_prediction_flux"
    if name in ROI_SET_BY_NAME or "roi_candidates" in name or "main_channel" in name or "trimmed_core" in name or "rescue" in name:
        return "roi"
    if "roi_qc_metrics" in name or name == "auto_roi_qc_metrics.csv":
        return "qc"
    if "hls_reflectance_timeseries" in name or name == "hls_features.csv":
        return "hls"
    if "sentinel2_reflectance" in name:
        return "optical"
    if "era5_land_daily" in name:
        return "era5"
    if "modis_snow_daily" in name or "snowmelt_windows" in name:
        return "modis"
    if "daily_hydroclimate_features" in name:
        return "hydroclimate"
    if "smap_soil_moisture" in name:
        return "smap"
    if name.startswith("auxiliary_context"):
        return "auxiliary"
    if "data/raw_external/arcticgro" in text:
        return "raw_external_arcticgro"
    if "data/raw/arcticgro" in text and "version_" in name and name.endswith(".xlsx"):
        return "discharge"
    if "data/raw/arcticgro" in text and "absorbance" in name:
        return "absorbance"
    if "data/raw/arcticgro" in text:
        return "raw_arcticgro"
    return "unknown"


def _target_table(family: str, file_name: str) -> tuple[bool, str, str]:
    if family == "roi" and file_name.lower() in ROI_SET_BY_NAME:
        return True, "roi_catalog", ""
    if family in {"era5", "modis", "hydroclimate"}:
        return True, "daily_hydroclimate_canonical", ""
    if family in {"hls", "optical"}:
        return True, "optical_timeseries_canonical", ""
    if family in {"smap", "auxiliary"}:
        return True, "auxiliary_context_canonical", ""
    if family in {"raw_arcticgro", "raw_external_arcticgro", "discharge", "absorbance"}:
        return False, "old_snapshot_raw_compare", "raw files require duplicate/conflict comparison, not direct canonical promotion"
    if family == "excluded_model_prediction_flux":
        return False, "", "model/prediction/flux artifacts are excluded"
    if family == "qc":
        return False, "", "QC file is used as sidecar evidence"
    return False, "", "no supported canonical target"


def _csv_metadata(file_path: Path) -> tuple[int | str, str, str, list[str]]:
    try:
        frame = pd.read_csv(file_path)
    except Exception:
        return "", "", "", []
    columns = [str(column) for column in frame.columns]
    date_min = ""
    date_max = ""
    for column in columns:
        if "date" in column.lower() or column.lower() in {"datetime", "time"}:
            dates = pd.to_datetime(frame[column], errors="coerce").dropna()
            if not dates.empty:
                date_min = dates.min().date().isoformat()
                date_max = dates.max().date().isoformat()
                break
    return len(frame), date_min, date_max, columns


def _xlsx_metadata(file_path: Path) -> tuple[int | str, str, str, list[str]]:
    try:
        workbook = pd.ExcelFile(file_path)
        row_count = 0
        columns: list[str] = []
        for sheet in workbook.sheet_names:
            preview = pd.read_excel(file_path, sheet_name=sheet, nrows=3)
            row_count += len(pd.read_excel(file_path, sheet_name=sheet, usecols=[0]))
            columns.extend(f"{sheet}:{column}" for column in preview.columns)
        return row_count, "", "", columns[:200]
    except Exception:
        return "", "", "", []


def _geojson_metadata(file_path: Path) -> tuple[int | str, str, str, list[str]]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        features = data.get("features") or []
        columns: set[str] = set()
        for feature in features:
            columns.update((feature.get("properties") or {}).keys())
        return len(features), "", "", sorted(columns)
    except Exception:
        return "", "", "", []


def _file_metadata(file_path: Path) -> tuple[int | str, str, str, list[str]]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _csv_metadata(file_path)
    if suffix in {".xlsx", ".xls"}:
        return _xlsx_metadata(file_path)
    if suffix == ".geojson":
        return _geojson_metadata(file_path)
    return "", "", "", []


def build_old_snapshot_inventory() -> pd.DataFrame:
    rows = []
    manifest = _snapshot_manifest()
    for _, record in manifest.iterrows():
        snapshot_path = str(record.get("local_path", ""))
        file_path = path(snapshot_path)
        original = str(record.get("original_relative_path", "")) or _original_relative_path(snapshot_path)
        file_name = Path(snapshot_path).name
        family = infer_product_family(original, file_name)
        promotable, target, reason = _target_table(family, file_name)
        row_count, date_min, date_max, columns = _file_metadata(file_path) if file_path.exists() else ("", "", "", [])
        fingerprint = hashlib.sha1("|".join(columns).encode("utf-8")).hexdigest()[:16] if columns else ""
        rows.append(
            {
                "snapshot_path": snapshot_path,
                "original_relative_path": original,
                "file_name": file_name,
                "file_extension": file_path.suffix.lower(),
                "sha256": record.get("sha256") or (sha256_file(file_path) if file_path.exists() else ""),
                "file_size_bytes": record.get("file_size_bytes") or (file_path.stat().st_size if file_path.exists() else ""),
                "old_project_subdir": _old_project_subdir(original),
                "inferred_river": _infer_river(file_path, original) if file_path.exists() else _infer_river_from_path(original),
                "inferred_product_family": family,
                "inferred_stage": _stage(original),
                "row_count": row_count,
                "date_min": date_min,
                "date_max": date_max,
                "columns_json": _safe_json(columns),
                "schema_fingerprint": fingerprint,
                "promotable_to_canonical": promotable,
                "target_canonical_table": target,
                "not_promoted_reason": reason,
            }
        )
    inventory = pd.DataFrame(rows, columns=INVENTORY_COLUMNS)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(TABLE_DIR / "old_snapshot_inventory.csv", index=False, encoding="utf-8")
    return inventory


def _load_inventory() -> pd.DataFrame:
    inventory_path = TABLE_DIR / "old_snapshot_inventory.csv"
    if inventory_path.exists():
        return pd.read_csv(inventory_path).fillna("")
    return build_old_snapshot_inventory()


def _version(value: Any) -> str:
    return version_from_text(value)


def compare_old_raw_to_official(inventory: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    inventory = inventory if inventory is not None else _load_inventory()
    old = inventory[inventory["inferred_product_family"].isin(["raw_arcticgro", "raw_external_arcticgro", "discharge", "absorbance"])].copy()
    manifest = read_manifest()
    official = manifest[
        manifest["source_id"].astype(str).str.startswith("arcticgro_")
        & (manifest["download_status"].astype(str).str.lower() == "downloaded")
        & ~manifest["local_path"].astype(str).str.contains("old_project_snapshot", na=False)
    ].copy()
    official["version"] = official.apply(lambda row: _version(f"{row.get('file_name','')} {row.get('version_detected','')}"), axis=1)
    rows = []
    station_rows = []
    for _, row in old.iterrows():
        old_sha = str(row.get("sha256", ""))
        old_name = str(row.get("file_name", ""))
        old_version = _version(f"{old_name} {row.get('original_relative_path','')}")
        same_hash_rows = official[official["sha256"].astype(str) == old_sha]
        same_name_rows = official[official["file_name"].astype(str).str.lower() == old_name.lower()]
        same_hash = not same_hash_rows.empty
        same_name = not same_name_rows.empty
        same_version = old_version != "" and official["version"].astype(str).eq(old_version).any()
        official_row = same_hash_rows.iloc[0] if same_hash else (same_name_rows.iloc[0] if same_name else (official[official["version"].astype(str) == old_version].iloc[0] if same_version else pd.Series(dtype=object)))
        if same_hash:
            decision = "duplicate_of_official_current"
        elif same_name and same_version:
            decision = "conflict_requires_audit"
        else:
            decision = "old_only_candidate"
        notes = "raw snapshot is not promoted directly to canonical"
        if "srednekolymsk" in old_name.lower():
            notes = "alternate Kolyma discharge station candidate; not promoted to main Kolyma discharge"
            station_rows.append(
                {
                    "old_snapshot_path": row.get("snapshot_path", ""),
                    "river": "Kolyma",
                    "station": "Srednekolymsk",
                    "version_detected": old_version,
                    "sha256": old_sha,
                    "decision": "candidate_station_not_promoted",
                    "notes": notes,
                }
            )
        rows.append(
            {
                "old_snapshot_path": row.get("snapshot_path", ""),
                "old_sha256": old_sha,
                "official_current_path": official_row.get("local_path", "") if not official_row.empty else "",
                "official_sha256": official_row.get("sha256", "") if not official_row.empty else "",
                "same_hash": same_hash,
                "same_version": same_version,
                "same_file_name": same_name,
                "decision": decision,
                "notes": notes,
            }
        )
    compare = pd.DataFrame(rows)
    station_inventory = pd.DataFrame(station_rows)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    compare.to_csv(TABLE_DIR / "old_snapshot_raw_compare.csv", index=False, encoding="utf-8")
    station_inventory.to_csv(TABLE_DIR / "discharge_candidate_station_inventory.csv", index=False, encoding="utf-8")
    return compare, station_inventory


def _read_geojson(file_path: Path) -> dict[str, Any]:
    return json.loads(file_path.read_text(encoding="utf-8"))


def _iter_positions(geometry: dict[str, Any]):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        for ring in coords:
            yield ring
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring


def _ring_area_m2(ring: list[list[float]]) -> float:
    if len(ring) < 3:
        return 0.0
    lats = [point[1] for point in ring if len(point) >= 2]
    mean_lat = math.radians(sum(lats) / len(lats)) if lats else 0.0
    points = [(point[0] * 111320.0 * math.cos(mean_lat), point[1] * 110540.0) for point in ring if len(point) >= 2]
    area = 0.0
    for idx, (x1, y1) in enumerate(points):
        x2, y2 = points[(idx + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _geojson_area_m2(data: dict[str, Any]) -> float | None:
    areas = []
    for feature in data.get("features") or []:
        for ring in _iter_positions(feature.get("geometry") or {}):
            areas.append(_ring_area_m2(ring))
    total = sum(areas)
    return total if total > 0 else None


def _roi_qc_by_river(inventory: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    qc = inventory[inventory["inferred_product_family"] == "qc"]
    for _, record in qc.iterrows():
        file_path = path(record["snapshot_path"])
        if not file_path.exists() or file_path.suffix.lower() != ".csv":
            continue
        try:
            frame = pd.read_csv(file_path)
        except Exception:
            continue
        for _, row in frame.iterrows():
            river = canonical_river(row.get("river", ""))
            if river:
                out[river] = row.to_dict()
    return out


def promote_roi(inventory: pd.DataFrame | None = None) -> pd.DataFrame:
    inventory = inventory if inventory is not None else _load_inventory()
    qc_by_river = _roi_qc_by_river(inventory)
    rows = []
    roi_records = inventory[
        (inventory["inferred_product_family"] == "roi")
        & inventory["file_name"].astype(str).str.lower().isin(ROI_SET_BY_NAME)
    ]
    for _, record in roi_records.iterrows():
        file_path = path(record["snapshot_path"])
        if not file_path.exists():
            continue
        data = _read_geojson(file_path)
        feature = (data.get("features") or [{}])[0]
        props = feature.get("properties") or {}
        river = canonical_river(props.get("river") or record.get("inferred_river", ""))
        qc = qc_by_river.get(river, {})
        area = props.get("roi_area_m2") or qc.get("roi_area_m2") or _geojson_area_m2(data)
        risk = props.get("final_risk_class") or qc.get("status") or "legacy_snapshot_requires_review"
        rows.append(
            {
                "river": river,
                "roi_set": ROI_SET_BY_NAME[str(record["file_name"]).lower()],
                "roi_path": record["snapshot_path"],
                "roi_exists": True,
                "roi_area_m2": area,
                "roi_source": props.get("primary_source") or props.get("source") or "old_project_snapshot",
                "roi_risk": risk,
                "manual_review_required": True,
                "source_id": SOURCE_ID,
                "snapshot_path": record["snapshot_path"],
                "original_relative_path": record["original_relative_path"],
                "sha256": record["sha256"],
                "quality_flag": QUALITY_ROI,
                "notes": f"legacy ROI promoted from old snapshot; properties={_safe_json(props)}; qc={_safe_json(qc)}",
            }
        )
    old_rows = ensure_columns(pd.DataFrame(rows), "roi_catalog")
    existing_path = PROCESSED_DIR / "roi_catalog.csv"
    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        if not existing.empty:
            existing = ensure_columns(existing, "roi_catalog")
            existing = existing[existing["source_id"].astype(str) != SOURCE_ID]
            existing = existing[existing["roi_set"].astype(str) != "not_configured"]
            combined = pd.concat([existing, old_rows], ignore_index=True)
        else:
            combined = old_rows
    else:
        combined = old_rows
    combined = ensure_columns(combined.drop_duplicates(["river", "roi_set", "source_id", "snapshot_path"], keep="last"), "roi_catalog")
    write_table(combined, "roi_catalog", existing_path)
    return combined


def _numeric(value: Any) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else None


def _column_by_norm(columns: list[str] | pd.Index, normalized_name: str) -> str | None:
    return next((column for column in columns if _norm(column) == normalized_name), None)


def _first_numeric(row: pd.Series, columns: list[str] | pd.Index, normalized_names: list[str]) -> float | None:
    for name in normalized_names:
        column = _column_by_norm(columns, name)
        if column is None:
            continue
        value = _numeric(row.get(column))
        if value is not None:
            return value
    return None


def _first_text(row: pd.Series, columns: list[str] | pd.Index, normalized_names: list[str]) -> str:
    for name in normalized_names:
        column = _column_by_norm(columns, name)
        if column is None:
            continue
        value = clean_text(row.get(column))
        if value:
            return value
    return ""


def _hydro_value(source_col_norm: str, value: Any) -> float | None:
    parsed = _numeric(value)
    if parsed is None:
        return None
    if source_col_norm == "temp2m_mean_k":
        return parsed - 273.15
    return parsed


def _river_from_frame(frame: pd.DataFrame, fallback: str) -> pd.Series:
    if "river" in frame.columns:
        return frame["river"].map(canonical_river)
    return pd.Series([fallback] * len(frame), index=frame.index)


def promote_hydroclimate(inventory: pd.DataFrame | None = None) -> pd.DataFrame:
    inventory = inventory if inventory is not None else _load_inventory()
    records = inventory[inventory["inferred_product_family"].isin(["era5", "modis", "hydroclimate"])].copy()
    records["_priority"] = records["inferred_product_family"].map({"hydroclimate": 3, "era5": 2, "modis": 1}).fillna(0)
    records = records.sort_values(["_priority", "snapshot_path"])
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    unmapped_rows = []
    mapped_source_columns = {"date", "datetime", "year", "doy", "sin_doy", "cos_doy"}
    for _, record in records.iterrows():
        file_path = path(record["snapshot_path"])
        if not file_path.exists() or file_path.suffix.lower() != ".csv":
            continue
        frame = pd.read_csv(file_path)
        if "date" not in frame.columns:
            continue
        fallback_river = canonical_river(record.get("inferred_river", ""))
        frame["_river"] = _river_from_frame(frame, fallback_river)
        frame["_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype("string")
        mapped_cols = {_norm(column): HYDRO_COLUMN_MAP[_norm(column)] for column in frame.columns if _norm(column) in HYDRO_COLUMN_MAP}
        unmapped = [
            column
            for column in frame.columns
            if column not in {"_river", "_date"}
            and _norm(column) not in HYDRO_COLUMN_MAP
            and _norm(column) not in HYDRO_QC_SIDECAR_COLUMNS
            and column not in mapped_source_columns
        ]
        if unmapped:
            unmapped_rows.append(
                {
                    "snapshot_path": record["snapshot_path"],
                    "original_relative_path": record["original_relative_path"],
                    "inferred_product_family": record["inferred_product_family"],
                    "unmapped_columns_json": _safe_json(unmapped),
                    "river": "",
                    "date": "",
                    "variable": "",
                    "value": "",
                    "unit": "",
                    "canonical_field": "",
                    "disposition": "file_level_unmapped_columns",
                    "notes": "columns retained outside daily_hydroclimate_canonical",
                }
            )
        for _, row in frame.iterrows():
            river = clean_text(row.get("_river"))
            date = clean_text(row.get("_date"))
            if not river or river.lower() in {"nan", "nat"} or not date or date.lower() in {"nan", "nat"}:
                continue
            key = (river, date)
            target = by_key.setdefault(
                key,
                {
                    "river": river,
                    "date": date,
                    "aggregation_geometry": "old_project_inferred",
                    "aggregation_geometry_id": "old_snapshot",
                    "temperature_2m_C": pd.NA,
                    "precipitation_m": pd.NA,
                    "snow_depth_m": pd.NA,
                    "snowmelt_m": pd.NA,
                    "surface_runoff_m": pd.NA,
                    "subsurface_runoff_m": pd.NA,
                    "total_runoff_m": pd.NA,
                    "positive_degree_day_Cday": pd.NA,
                    "snow_cover_fraction": pd.NA,
                    "snow_depletion_rate_7d": pd.NA,
                    "source_id": SOURCE_ID,
                    "quality_flag": QUALITY_HYDRO,
                    "snapshot_path": set(),
                    "original_relative_path": set(),
                    "sha256": set(),
                    "notes": set(),
                    "_converted_fields": set(),
                },
            )
            for source_col_norm, target_col in mapped_cols.items():
                source_col = next(column for column in frame.columns if _norm(column) == source_col_norm)
                value = _hydro_value(source_col_norm, row.get(source_col))
                converted_field = target_col in target["_converted_fields"]
                if value is not None and (pd.isna(target.get(target_col)) or converted_field):
                    target[target_col] = value
                    target["_converted_fields"].discard(target_col)
                    if source_col_norm == "temp2m_mean_k":
                        target["notes"].add("legacy conversion temp2m_mean_K - 273.15 to temperature_2m_C")
                    if converted_field:
                        target["notes"].add(f"explicit {source_col} replaced prior legacy conversion for {target_col}")
            ndsi_col = _column_by_norm(frame.columns, "mean_ndsi_snow_cover")
            ndsi_value = _numeric(row.get(ndsi_col)) if ndsi_col else None
            if ndsi_value is not None:
                if 0 <= ndsi_value <= 100 and pd.isna(target.get("snow_cover_fraction")):
                    target["snow_cover_fraction"] = ndsi_value / 100.0
                    target["_converted_fields"].add("snow_cover_fraction")
                    disposition = "converted_to_snow_cover_fraction"
                    notes = "legacy conversion mean_ndsi_snow_cover / 100 to snow_cover_fraction"
                    target["notes"].add(notes)
                elif 0 <= ndsi_value <= 100:
                    disposition = "retained_sidecar_existing_snow_cover_fraction"
                    notes = "canonical snow_cover_fraction already populated; mean_ndsi_snow_cover retained as QC sidecar"
                else:
                    disposition = "invalid_provider_value_not_converted"
                    notes = "mean_ndsi_snow_cover outside 0-100 range; retained as QC sidecar"
                unmapped_rows.append(
                    {
                        "snapshot_path": record["snapshot_path"],
                        "original_relative_path": record["original_relative_path"],
                        "inferred_product_family": record["inferred_product_family"],
                        "unmapped_columns_json": "",
                        "river": river,
                        "date": date,
                        "variable": "mean_ndsi_snow_cover",
                        "value": ndsi_value,
                        "unit": "percent",
                        "canonical_field": "snow_cover_fraction",
                        "disposition": disposition,
                        "notes": notes,
                    }
                )
            valid_pixels_col = _column_by_norm(frame.columns, "valid_modis_pixels")
            valid_pixels = _numeric(row.get(valid_pixels_col)) if valid_pixels_col else None
            if valid_pixels is not None:
                unmapped_rows.append(
                    {
                        "snapshot_path": record["snapshot_path"],
                        "original_relative_path": record["original_relative_path"],
                        "inferred_product_family": record["inferred_product_family"],
                        "unmapped_columns_json": "",
                        "river": river,
                        "date": date,
                        "variable": "valid_modis_pixels",
                        "value": valid_pixels,
                        "unit": "pixels",
                        "canonical_field": "",
                        "disposition": "retained_qc_sidecar",
                        "notes": "MODIS valid pixel count retained outside daily_hydroclimate_canonical",
                    }
                )
            target["snapshot_path"].add(record["snapshot_path"])
            target["original_relative_path"].add(record["original_relative_path"])
            target["sha256"].add(record["sha256"])
            target["notes"].add(f"{record['inferred_product_family']}:{record['file_name']}")
    rows = []
    for item in by_key.values():
        temp = _numeric(item.get("temperature_2m_C"))
        if pd.isna(item.get("positive_degree_day_Cday")) and temp is not None:
            item["positive_degree_day_Cday"] = max(temp, 0.0)
        item.pop("_converted_fields", None)
        for column in ["snapshot_path", "original_relative_path", "sha256", "notes"]:
            item[column] = ";".join(sorted(str(value) for value in item[column] if str(value)))
        rows.append(item)
    old_rows = pd.DataFrame(rows)
    if not old_rows.empty:
        old_rows["date_dt"] = pd.to_datetime(old_rows["date"], errors="coerce")
        old_rows = old_rows.sort_values(["river", "date_dt"])
        old_rows["snow_depletion_rate_7d"] = old_rows.groupby("river")["snow_cover_fraction"].transform(lambda series: pd.to_numeric(series, errors="coerce").diff(7))
        old_rows = old_rows.drop(columns=["date_dt"])
    old_rows = ensure_columns(old_rows, "daily_hydroclimate_canonical")
    pd.DataFrame(unmapped_rows).to_csv(TABLE_DIR / "old_snapshot_hydroclimate_unmapped_columns.csv", index=False, encoding="utf-8")
    existing_path = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    existing = pd.read_csv(existing_path) if existing_path.exists() else pd.DataFrame()
    if not existing.empty:
        existing = ensure_columns(existing, "daily_hydroclimate_canonical")
        non_old = existing[existing["source_id"].astype(str) != SOURCE_ID]
        non_old_keys = set(zip(non_old["river"].astype(str), non_old["date"].astype(str)))
        if not old_rows.empty:
            old_keys = list(zip(old_rows["river"].astype(str), old_rows["date"].astype(str)))
            old_rows = old_rows[[key not in non_old_keys for key in old_keys]]
        combined = pd.concat([non_old, old_rows], ignore_index=True)
    else:
        combined = old_rows
    write_table(ensure_columns(combined, "daily_hydroclimate_canonical"), "daily_hydroclimate_canonical", existing_path)
    return ensure_columns(combined, "daily_hydroclimate_canonical")


def promote_optical(inventory: pd.DataFrame | None = None) -> pd.DataFrame:
    inventory = inventory if inventory is not None else _load_inventory()
    records = inventory[inventory["inferred_product_family"].isin(["hls", "optical"])].copy()
    records["_priority"] = records["file_name"].map(lambda name: 2 if str(name).lower() == "hls_features.csv" else 1)
    records = records.sort_values(["_priority", "snapshot_path"])
    rows = []
    for _, record in records.iterrows():
        file_path = path(record["snapshot_path"])
        if not file_path.exists() or file_path.suffix.lower() != ".csv":
            continue
        frame = pd.read_csv(file_path)
        if "date" not in frame.columns:
            continue
        fallback_river = canonical_river(record.get("inferred_river", ""))
        frame["_river"] = _river_from_frame(frame, fallback_river)
        for _, row in frame.iterrows():
            river = clean_text(row.get("_river"))
            date = pd.to_datetime(row.get("date"), errors="coerce")
            if not river or pd.isna(date):
                continue
            is_sentinel2 = record["inferred_product_family"] == "optical" or "sentinel2" in str(record["file_name"]).lower()
            if is_sentinel2:
                collection = clean_text(row.get("collection")) or "COPERNICUS/S2_SR_HARMONIZED_legacy_snapshot"
                sensor = "Sentinel-2"
                processing_level = "legacy_snapshot_sentinel2"
                roi_set = "final_primary"
                pixel_size = _first_numeric(row, frame.columns, ["pixel_size_m"]) or 10
                mask_method = _first_text(row, frame.columns, ["cloud_snow_water_mask_method", "snow_ice_flag"]) or "legacy Sentinel-2 SCL cloud-snow-water method"
                notes = f"legacy Sentinel-2 optical proxy promoted from old snapshot; source_file={record['file_name']}"
            else:
                collection = clean_text(row.get("collection")) or "NASA/HLS/S30_L30_legacy_mixed"
                sensor = "HLS"
                processing_level = "legacy_snapshot_hls"
                roi_set = clean_text(row.get("roi_set")) or "old_project_active_or_unknown_roi"
                pixel_size = _first_numeric(row, frame.columns, ["pixel_size_m"]) or 30
                mask_method = _first_text(row, frame.columns, ["cloud_or_snow_mask_notes", "cloud_snow_water_mask_method"]) or "legacy HLS Fmask/water-mask method"
                notes = f"legacy HLS optical proxy promoted from old snapshot; source_file={record['file_name']}"
            values = {}
            for source_col_norm, target_col in OPTICAL_COLUMN_MAP.items():
                source_col = next((column for column in frame.columns if _norm(column) == source_col_norm), None)
                if source_col and (target_col not in values or values[target_col] is None):
                    values[target_col] = _numeric(row.get(source_col))
            n_valid = _first_numeric(row, frame.columns, ["n_valid_water_pixels", "valid_water_pixels"])
            n_total = _first_numeric(row, frame.columns, ["n_total_pixels", "total_pixels"])
            pct_valid = _first_numeric(row, frame.columns, ["pct_valid_water_pixels"])
            if pct_valid is None and n_valid is not None and n_total not in {None, 0}:
                pct_valid = 100.0 * n_valid / n_total
            rows.append(
                {
                    "river": river,
                    "date": date.date().isoformat(),
                    "datetime": clean_text(row.get("datetime")) or date.isoformat(),
                    "sensor": sensor,
                    "collection": collection,
                    "processing_level": processing_level,
                    "roi_set": roi_set,
                    "pixel_size_m": pixel_size,
                    "blue": values.get("blue"),
                    "green": values.get("green"),
                    "red": values.get("red"),
                    "nir": values.get("nir"),
                    "swir1": values.get("swir1"),
                    "swir2": values.get("swir2"),
                    "ndwi": _first_numeric(row, frame.columns, ["ndwi", "ndwi_median", "ndwi_mean"]),
                    "mndwi": _first_numeric(row, frame.columns, ["mndwi", "mndwi_median", "mndwi_mean"]),
                    "red_green_ratio": _first_numeric(row, frame.columns, ["red_green_ratio", "red_green_ratio_median", "red_green_ratio_mean"]),
                    "green_blue_ratio": _first_numeric(row, frame.columns, ["green_blue_ratio", "green_blue_ratio_median", "green_blue_ratio_mean"]),
                    "n_valid_water_pixels": n_valid,
                    "n_total_pixels": n_total,
                    "pct_valid_water_pixels": pct_valid,
                    "cloud_snow_water_mask_method": mask_method,
                    "image_id": clean_text(row.get("image_id")),
                    "source_id": SOURCE_ID,
                    "quality_flag": QUALITY_OPTICAL,
                    "snapshot_path": record["snapshot_path"],
                    "original_relative_path": record["original_relative_path"],
                    "sha256": record["sha256"],
                    "notes": notes,
                }
            )
    old_rows = ensure_columns(pd.DataFrame(rows), "optical_timeseries_canonical")
    if not old_rows.empty:
        old_rows = old_rows.drop_duplicates(["river", "date", "datetime", "image_id", "roi_set", "sensor"], keep="last")
    existing_path = PROCESSED_DIR / "optical_timeseries_canonical.csv"
    existing = pd.read_csv(existing_path) if existing_path.exists() else pd.DataFrame()
    if not existing.empty:
        existing = ensure_columns(existing, "optical_timeseries_canonical")
        non_old = existing[existing["source_id"].astype(str) != SOURCE_ID]
        non_old_keys = set(zip(non_old["river"].astype(str), non_old["date"].astype(str), non_old["image_id"].astype(str), non_old["roi_set"].astype(str), non_old["sensor"].astype(str)))
        if not old_rows.empty:
            old_keys = list(zip(old_rows["river"].astype(str), old_rows["date"].astype(str), old_rows["image_id"].astype(str), old_rows["roi_set"].astype(str), old_rows["sensor"].astype(str)))
            old_rows = old_rows[[key not in non_old_keys for key in old_keys]]
        combined = pd.concat([non_old, old_rows], ignore_index=True)
    else:
        combined = old_rows
    write_table(ensure_columns(combined, "optical_timeseries_canonical"), "optical_timeseries_canonical", existing_path)
    return ensure_columns(combined, "optical_timeseries_canonical")


def promote_auxiliary(inventory: pd.DataFrame | None = None) -> pd.DataFrame:
    inventory = inventory if inventory is not None else _load_inventory()
    records = inventory[inventory["inferred_product_family"].isin(["auxiliary", "smap"])].copy()
    rows = []
    for _, record in records.iterrows():
        file_path = path(record["snapshot_path"])
        if not file_path.exists() or file_path.suffix.lower() != ".csv":
            continue
        frame = pd.read_csv(file_path)
        fallback_river = canonical_river(record.get("inferred_river", ""))
        if "river" not in frame.columns and not fallback_river:
            continue
        river_series = _river_from_frame(frame, fallback_river)
        id_cols = {"river", "date", "year", "doy", "station_name", "notes"}
        for idx, row in frame.iterrows():
            river = clean_text(river_series.loc[idx])
            if not river:
                continue
            date = clean_text(row.get("date"))
            year = row.get("year")
            for column in frame.columns:
                if column in id_cols:
                    continue
                value = row.get(column)
                if pd.isna(value):
                    continue
                rows.append(
                    {
                        "river": river,
                        "year": year,
                        "date": date,
                        "context_family": record["inferred_product_family"],
                        "variable": column,
                        "value": value,
                        "unit": "",
                        "source_id": SOURCE_ID,
                        "snapshot_path": record["snapshot_path"],
                        "original_relative_path": record["original_relative_path"],
                        "sha256": record["sha256"],
                        "quality_flag": QUALITY_AUX,
                        "notes": f"legacy auxiliary context promoted from old snapshot; file={record['file_name']}",
                    }
                )
    old_rows = ensure_columns(pd.DataFrame(rows), "auxiliary_context_canonical")
    existing_path = PROCESSED_DIR / "auxiliary_context_canonical.csv"
    existing = pd.read_csv(existing_path) if existing_path.exists() else pd.DataFrame()
    if not existing.empty:
        existing = ensure_columns(existing, "auxiliary_context_canonical")
        existing = existing[existing["source_id"].astype(str) != SOURCE_ID]
        combined = pd.concat([existing, old_rows], ignore_index=True)
    else:
        combined = old_rows
    write_table(ensure_columns(combined, "auxiliary_context_canonical"), "auxiliary_context_canonical", existing_path)
    return ensure_columns(combined, "auxiliary_context_canonical")


def _promotion_summary() -> pd.DataFrame:
    rows = []
    for table_name in ["roi_catalog", "daily_hydroclimate_canonical", "optical_timeseries_canonical", "auxiliary_context_canonical"]:
        table_path = PROCESSED_DIR / f"{table_name}.csv"
        if not table_path.exists():
            continue
        frame = pd.read_csv(table_path)
        old_count = int((frame.get("source_id", pd.Series(dtype=str)).astype(str) == SOURCE_ID).sum()) if not frame.empty else 0
        rows.append({"target_canonical_table": table_name, "source_id": SOURCE_ID, "promoted_rows": old_count})
    summary = pd.DataFrame(rows)
    summary.to_csv(TABLE_DIR / "old_snapshot_promotion_summary.csv", index=False, encoding="utf-8")
    return summary


def audit_old_snapshot() -> tuple[pd.DataFrame, pd.DataFrame]:
    inventory = build_old_snapshot_inventory()
    raw_compare, _ = compare_old_raw_to_official(inventory)
    _promotion_summary()
    return inventory, raw_compare


def promote_old_snapshot(families: list[str]) -> pd.DataFrame:
    inventory = build_old_snapshot_inventory()
    normalized = {family.strip().lower() for family in families}
    if "raw_compare" in normalized:
        compare_old_raw_to_official(inventory)
    if "roi" in normalized:
        promote_roi(inventory)
    if "hydroclimate" in normalized:
        promote_hydroclimate(inventory)
    if "optical" in normalized:
        promote_optical(inventory)
    if "auxiliary" in normalized:
        promote_auxiliary(inventory)
    return _promotion_summary()
