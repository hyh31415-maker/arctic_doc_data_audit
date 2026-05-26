from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .manifest import sha256_file
from .normalize import load_rivers
from .paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs, path, relpath


NO_MODEL_TEXT = "No DOC model was trained. No DOC prediction was generated. No flux was generated."
GOLD_DIR = PROCESSED_DIR / "gold"
GOLD_REPORT_DIR = REPORT_DIR / "gold"
GOLD_TABLE_DIR = TABLE_DIR / "gold"
LEGACY_SOURCE = "old_arctic_doc_snowmelt_untrained_data"
RIVERS = list(load_rivers().keys())
HYDRO_VARS = [
    "temperature_2m_C",
    "precipitation_m",
    "snow_depth_m",
    "snowmelt_m",
    "surface_runoff_m",
    "subsurface_runoff_m",
    "total_runoff_m",
    "positive_degree_day_Cday",
    "snow_cover_fraction",
    "snow_depletion_rate_7d",
]
OPTICAL_COLUMNS = [
    "blue",
    "green",
    "red",
    "nir",
    "swir1",
    "swir2",
    "ndwi",
    "mndwi",
    "red_green_ratio",
    "green_blue_ratio",
]
LAB_FORBIDDEN = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}
ID_TOPOLOGY_FIELDS = {
    "HYBAS_ID",
    "HYBAS_ID_mean",
    "NEXT_DOWN",
    "NEXT_DOWN_mean",
    "NEXT_SINK",
    "NEXT_SINK_mean",
    "MAIN_BAS",
    "MAIN_BAS_mean",
    "PFAF_ID",
    "PFAF_ID_mean",
    "SORT",
    "SORT_mean",
    "OBJECTID",
    "BAS_ID",
    "HYRIV_ID",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_gold_dirs() -> None:
    ensure_project_dirs()
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def _read_processed(name: str) -> pd.DataFrame:
    p = PROCESSED_DIR / f"{name}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, low_memory=False).fillna("")


def _read_output_table(name: str) -> pd.DataFrame:
    p = TABLE_DIR / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, low_memory=False).fillna("")


def _read_gold(name: str) -> pd.DataFrame:
    p = GOLD_DIR / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, low_memory=False).fillna("")


def _write_csv(frame: pd.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    return destination


def _md_table(frame: pd.DataFrame, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes", "y"})


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _source_priority(source_id: Any, quality_flag: Any = "") -> int:
    source = str(source_id)
    quality = str(quality_flag)
    if quality == "regenerated_gee" or source.startswith("gee_"):
        return 1
    if source in {"arcticgro_discharge_current", "arcticgro_water_quality_current"}:
        return 1
    if "official" in source or "arcticgro" in source:
        return 2
    if source == LEGACY_SOURCE:
        return 3
    return 2


def _sensor_priority(sensor: Any) -> int:
    order = {"HLS": 1, "Sentinel-2": 2, "Landsat": 3}
    return order.get(str(sensor), 9)


def _safe_column(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path(), text=True).strip()
    except Exception:
        return "unknown"


def _gold_path(name: str) -> Path:
    return GOLD_DIR / name


def final_data_clean() -> Path:
    ensure_gold_dirs()
    inputs = [
        "doc_labels_canonical",
        "daily_discharge_canonical",
        "daily_hydroclimate_canonical",
        "optical_timeseries_canonical",
        "basin_context_canonical",
        "roi_catalog",
        "lab_optical_proxy_canonical",
    ]
    rows = []
    for name in inputs:
        frame = _read_processed(name)
        rows.append({"input_table": f"data/processed/{name}.csv", "rows": len(frame), "columns": len(frame.columns)})
    summary = pd.DataFrame(rows)
    _write_csv(summary, GOLD_TABLE_DIR / "final_input_canonical_summary.csv")
    lines = [
        "# Final Data Cleaning Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "This stage locks the already-audited canonical layer into gold outputs. It does not query new sources and does not read raw/interim files.",
        "",
        "## Input Canonical Tables",
        _md_table(summary),
        "",
        "## Cleaning Contract",
        "- DOC labels remain ArcticGRO canonical preferred DOC records.",
        "- Candidate labels are not promoted by default.",
        "- GEE regenerated rows are preferred over legacy rows.",
        "- Lab absorbance/CDOM is excluded from production daily matrices.",
        "- HydroATLAS topology and identifier fields are metadata only, not predictors.",
    ]
    out = GOLD_REPORT_DIR / "final_data_cleaning_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_doc_labels_gold() -> pd.DataFrame:
    labels = _read_processed("doc_labels_canonical")
    if labels.empty:
        out = pd.DataFrame()
    else:
        mask = (
            labels["parameter_canonical"].astype(str).eq("DOC")
            & _bool_series(labels["preferred_record"])
            & _bool_series(labels["can_train_doc_model"])
            & ~_bool_series(labels["is_toc_not_doc"])
        )
        out = labels.loc[mask].copy()
        out["value_mgC_L"] = _num(out["value_mgC_L"])
        out = out.sort_values(["river", "date", "label_id"]).drop_duplicates("label_id", keep="first")
    exclusions = labels.loc[~labels.index.isin(out.index)].copy() if not labels.empty else pd.DataFrame()
    if not exclusions.empty:
        exclusions["gold_exclusion_reason"] = np.select(
            [
                exclusions["parameter_canonical"].astype(str).ne("DOC"),
                ~_bool_series(exclusions["preferred_record"]),
                ~_bool_series(exclusions["can_train_doc_model"]),
                _bool_series(exclusions["is_toc_not_doc"]),
            ],
            ["not_doc", "not_preferred_record", "cannot_train_doc_model", "toc_not_doc"],
            default=exclusions.get("exclusion_reason", ""),
        )
    _write_csv(exclusions, GOLD_TABLE_DIR / "doc_label_gold_exclusions.csv")
    _write_csv(out, _gold_path("doc_labels_gold.csv"))
    return out


def build_daily_discharge_gold() -> pd.DataFrame:
    discharge = _read_processed("daily_discharge_canonical")
    if discharge.empty:
        out = pd.DataFrame()
        _write_csv(out, GOLD_TABLE_DIR / "discharge_duplicate_resolution.csv")
        _write_csv(out, _gold_path("daily_discharge_gold.csv"))
        return out
    df = discharge.copy()
    df["date"] = _date(df["date"]).dt.date.astype(str)
    df["Q_m3s"] = _num(df["Q_m3s"])
    df["_priority"] = df.apply(lambda row: _source_priority(row.get("source_id", ""), row.get("quality_flag", "")), axis=1)
    df["_complete"] = df["Q_m3s"].notna().astype(int)
    df["_group_size"] = df.groupby(["river", "date"])["river"].transform("size")
    df["duplicate_group_id"] = np.where(df["_group_size"] > 1, "Q_" + df["river"].astype(str) + "_" + df["date"].astype(str), "")
    df = df.sort_values(["river", "date", "_priority", "_complete"], ascending=[True, True, True, False])
    df["is_primary_discharge"] = ~df.duplicated(["river", "date"], keep="first")
    resolution = df[df["_group_size"] > 1][
        ["river", "date", "source_id", "Q_m3s", "duplicate_group_id", "is_primary_discharge", "quality_flag", "notes"]
    ].copy()
    _write_csv(resolution, GOLD_TABLE_DIR / "discharge_duplicate_resolution.csv")
    out_cols = [
        "river",
        "station",
        "date",
        "Q_m3s",
        "source_id",
        "dataset_version",
        "original_value",
        "original_unit",
        "quality_flag",
        "provenance_tier",
        "is_primary_discharge",
        "duplicate_group_id",
        "notes",
    ]
    out = df[df["is_primary_discharge"]].copy()
    _write_csv(out[out_cols], _gold_path("daily_discharge_gold.csv"))
    return out[out_cols]


def _hydro_long() -> pd.DataFrame:
    hydro = _read_processed("daily_hydroclimate_canonical")
    if hydro.empty:
        return pd.DataFrame()
    df = hydro.copy()
    df["date"] = _date(df["date"]).dt.date.astype(str)
    id_cols = ["river", "date", "aggregation_geometry", "aggregation_geometry_id", "source_id", "quality_flag", "notes"]
    long = df.melt(id_vars=id_cols, value_vars=[v for v in HYDRO_VARS if v in df.columns], var_name="variable", value_name="value")
    long["value_num"] = _num(long["value"])
    long = long[long["value_num"].notna()].copy()
    long["_priority"] = long.apply(lambda row: _source_priority(row.get("source_id", ""), row.get("quality_flag", "")), axis=1)
    long["_source_sort"] = long["source_id"].astype(str)
    return long


def build_daily_hydroclimate_gold() -> pd.DataFrame:
    long = _hydro_long()
    if long.empty:
        out = pd.DataFrame(columns=["river", "date", *HYDRO_VARS])
        _write_csv(out, _gold_path("daily_hydroclimate_gold.csv"))
        return out
    selected = (
        long.sort_values(["river", "date", "variable", "_priority", "_source_sort"])
        .drop_duplicates(["river", "date", "variable"], keep="first")
        .copy()
    )
    values = selected.pivot_table(index=["river", "date"], columns="variable", values="value_num", aggfunc="first").reset_index()
    sources = selected.pivot_table(index=["river", "date"], columns="variable", values="source_id", aggfunc="first").reset_index()
    qualities = selected.pivot_table(index=["river", "date"], columns="variable", values="quality_flag", aggfunc="first").reset_index()
    base = (
        selected.sort_values(["river", "date", "_priority"])
        .drop_duplicates(["river", "date"], keep="first")[["river", "date", "aggregation_geometry", "aggregation_geometry_id", "notes"]]
    )
    out = base.merge(values, on=["river", "date"], how="outer")
    for variable in HYDRO_VARS:
        if variable not in out.columns:
            out[variable] = np.nan
    temp_source = sources[["river", "date", "temperature_2m_C"]].rename(columns={"temperature_2m_C": "source_id_temperature"}) if "temperature_2m_C" in sources.columns else pd.DataFrame(columns=["river", "date", "source_id_temperature"])
    snow_source_col = "snow_cover_fraction" if "snow_cover_fraction" in sources.columns else ("snow_depletion_rate_7d" if "snow_depletion_rate_7d" in sources.columns else "")
    snow_source = sources[["river", "date", snow_source_col]].rename(columns={snow_source_col: "source_id_snow"}) if snow_source_col else pd.DataFrame(columns=["river", "date", "source_id_snow"])
    runoff_source_col = "surface_runoff_m" if "surface_runoff_m" in sources.columns else ("total_runoff_m" if "total_runoff_m" in sources.columns else "")
    runoff_source = sources[["river", "date", runoff_source_col]].rename(columns={runoff_source_col: "source_id_runoff"}) if runoff_source_col else pd.DataFrame(columns=["river", "date", "source_id_runoff"])
    out = out.merge(temp_source, on=["river", "date"], how="left").merge(snow_source, on=["river", "date"], how="left").merge(runoff_source, on=["river", "date"], how="left")
    quality_flags = []
    q_lookup = qualities.set_index(["river", "date"]).to_dict("index") if not qualities.empty else {}
    for _, row in out.iterrows():
        qrow = q_lookup.get((row["river"], row["date"]), {})
        flags = sorted({str(v) for k, v in qrow.items() if k in HYDRO_VARS and str(v)})
        quality_flags.append(";".join(flags))
    out["quality_flag"] = quality_flags
    ordered = [
        "river",
        "date",
        "aggregation_geometry",
        "aggregation_geometry_id",
        *HYDRO_VARS,
        "source_id_temperature",
        "source_id_snow",
        "source_id_runoff",
        "quality_flag",
        "notes",
    ]
    out = out[ordered].sort_values(["river", "date"])
    _write_csv(selected, GOLD_TABLE_DIR / "hydroclimate_source_resolution.csv")
    legacy = long[long["source_id"].astype(str).eq(LEGACY_SOURCE)]
    regen = long[long["source_id"].astype(str).str.startswith("gee_")]
    compare = regen.merge(legacy, on=["river", "date", "variable"], suffixes=("_regenerated", "_legacy"))
    if not compare.empty:
        compare["difference"] = compare["value_num_regenerated"] - compare["value_num_legacy"]
        compare["status"] = "regenerated_used_legacy_reference"
    _write_csv(compare, GOLD_TABLE_DIR / "hydroclimate_legacy_vs_regenerated_used.csv")
    _write_csv(out, _gold_path("daily_hydroclimate_gold.csv"))
    return out


def build_optical_timeseries_gold() -> pd.DataFrame:
    optical = _read_processed("optical_timeseries_canonical")
    if optical.empty:
        out = pd.DataFrame()
        _write_csv(out, _gold_path("optical_timeseries_gold.csv"))
        return out
    df = optical.copy()
    df["date"] = _date(df["date"]).dt.date.astype(str)
    df["datetime_sort"] = pd.to_datetime(df.get("datetime", df["date"]), errors="coerce")
    for col in OPTICAL_COLUMNS + ["n_valid_water_pixels", "n_total_pixels", "pct_valid_water_pixels"]:
        if col in df.columns:
            df[col] = _num(df[col])
    df["pct_valid_water_pixels"] = np.where(df["pct_valid_water_pixels"] > 1, df["pct_valid_water_pixels"] / 100.0, df["pct_valid_water_pixels"])
    df["_priority"] = df.apply(lambda row: _source_priority(row.get("source_id", ""), row.get("quality_flag", "")), axis=1)
    df["_valid"] = df["pct_valid_water_pixels"].fillna(-1)
    df = df.sort_values(["river", "date", "sensor", "image_id", "roi_set", "_priority", "_valid"], ascending=[True, True, True, True, True, True, False])
    keys = ["river", "date", "sensor", "image_id", "roi_set"]
    df["is_primary_optical_row"] = ~df.duplicated(keys, keep="first")
    summary = df.groupby(["sensor", "source_id", "collection"], dropna=False).size().reset_index(name="rows")
    _write_csv(summary, GOLD_TABLE_DIR / "optical_band_mapping_summary.csv")
    keep = [
        "river",
        "date",
        "datetime",
        "sensor",
        "collection",
        "processing_level",
        "roi_set",
        "pixel_size_m",
        *OPTICAL_COLUMNS,
        "n_valid_water_pixels",
        "n_total_pixels",
        "pct_valid_water_pixels",
        "cloud_snow_water_mask_method",
        "image_id",
        "source_id",
        "quality_flag",
        "is_primary_optical_row",
        "notes",
    ]
    out = df[keep].copy()
    _write_csv(out, _gold_path("optical_timeseries_gold.csv"))
    return out


def build_simple_gold_copies() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    basin = _read_processed("basin_context_canonical")
    basin = basin.copy()
    _write_csv(basin, _gold_path("basin_context_gold.csv"))
    roi = _read_processed("roi_catalog")
    _write_csv(roi, _gold_path("roi_catalog_gold.csv"))
    lab = _read_processed("lab_optical_proxy_canonical")
    if not lab.empty and "can_be_daily_predictor" in lab.columns:
        lab["can_be_daily_predictor"] = False
    _write_csv(lab, _gold_path("lab_optical_proxy_gold.csv"))
    return basin, roi, lab


def _attribute_category(name: str) -> str:
    text = name.lower()
    if any(token in text for token in ["dis_", "run_", "inu_", "riv_", "dor_", "ria_", "rev_"]):
        return "hydrology"
    if any(token in text for token in ["ele_", "slp_", "gwt_", "sgr_", "area", "relief"]):
        return "physiography"
    if any(token in text for token in ["lka_", "lkv_", "lake", "reservoir"]):
        return "water_lake"
    if any(token in text for token in ["tmp", "pre", "pet", "aet", "ari", "climate", "snow"]):
        return "climate"
    if any(token in text for token in ["lc_", "wet", "soil", "for_", "geo", "veg"]):
        return "landcover_soil_geology"
    if any(token in text for token in ["pop", "dam", "gdp", "urb", "use", "irr"]):
        return "anthropogenic"
    return "other"


def build_basin_attributes_curated() -> tuple[pd.DataFrame, pd.DataFrame]:
    basin = _read_gold("basin_context_gold.csv")
    agg = _read_output_table("upstream_basin_aggregation.csv")
    rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for _, basin_row in basin.iterrows():
        river = str(basin_row.get("river", ""))
        try:
            attrs = json.loads(str(basin_row.get("hydroatlas_attributes_json", "{}")) or "{}")
        except Exception:
            attrs = {}
        agg_row = agg[agg["river"].astype(str).eq(river)].iloc[0].to_dict() if not agg.empty and (agg["river"].astype(str).eq(river)).any() else {}
        for key, value in attrs.items():
            raw_rows.append({"river": river, "source_field": key, "raw_value": value})
            if key in {"rows_matched", "columns_available", "sample_columns"}:
                continue
            base_name = key[:-5] if key.endswith("_mean") else key
            excluded_reason = ""
            if key in ID_TOPOLOGY_FIELDS or base_name in ID_TOPOLOGY_FIELDS:
                excluded_reason = "id_or_topology_field"
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            category = _attribute_category(key)
            model_use = bool(not excluded_reason and pd.notna(numeric) and category != "other")
            if excluded_reason:
                excluded.append({"river": river, "source_field": key, "exclusion_reason": excluded_reason, "notes": "Identifier/topology field kept out of predictors."})
            rows.append(
                {
                    "river": river,
                    "upstream_area_km2": basin_row.get("upstream_area_km2", ""),
                    "n_upstream_subbasins": agg_row.get("n_upstream_subbasins", ""),
                    "basin_id": basin_row.get("basin_id", ""),
                    "pfaf_id": basin_row.get("pfaf_id", ""),
                    "attribute_name": _safe_column(base_name),
                    "attribute_value": numeric if pd.notna(numeric) else value,
                    "attribute_unit_if_known": "",
                    "attribute_category": category,
                    "aggregation_method": "simple_mean_from_upstream_subbasins" if key.endswith("_mean") else "raw_summary_not_for_modeling",
                    "model_use": model_use,
                    "mechanism_use": bool(not excluded_reason and category != "other"),
                    "needs_area_weighted_refinement": bool(key.endswith("_mean")),
                    "source_field": key,
                    "source_id": basin_row.get("source_id", ""),
                    "quality_flag": basin_row.get("quality_flag", ""),
                    "notes": "Curated from HydroATLAS upstream summary; ID/topology fields excluded from predictors.",
                }
            )
    curated = pd.DataFrame(rows)
    if not curated.empty:
        curated = curated.drop_duplicates(["river", "source_field"], keep="first")
    _write_csv(curated, _gold_path("basin_attributes_curated.csv"))
    model = curated[curated["model_use"].astype(bool)].copy() if not curated.empty else pd.DataFrame()
    if not model.empty:
        model["wide_name"] = "basin_" + model["attribute_name"].astype(str)
        wide = model.pivot_table(index="river", columns="wide_name", values="attribute_value", aggfunc="first").reset_index()
    else:
        wide = pd.DataFrame({"river": RIVERS})
    _write_csv(wide, _gold_path("basin_attributes_curated_wide.csv"))
    dictionary = curated[["source_field", "attribute_name", "attribute_category", "aggregation_method", "model_use", "mechanism_use", "needs_area_weighted_refinement", "notes"]].drop_duplicates() if not curated.empty else pd.DataFrame()
    _write_csv(dictionary, GOLD_TABLE_DIR / "hydroatlas_attribute_dictionary_selected.csv")
    _write_csv(pd.DataFrame(excluded), GOLD_TABLE_DIR / "hydroatlas_attribute_exclusion_log.csv")
    _write_csv(pd.DataFrame(raw_rows), GOLD_TABLE_DIR / "hydroatlas_attribute_raw_summary.csv")
    return curated, wide


def build_gold_tables() -> None:
    ensure_gold_dirs()
    build_doc_labels_gold()
    build_daily_discharge_gold()
    build_daily_hydroclimate_gold()
    build_optical_timeseries_gold()
    build_simple_gold_copies()
    build_basin_attributes_curated()
    generate_final_qa_reports()
    generate_data_dictionary()


def _hydro_quality_for_matrix(hydro: pd.DataFrame) -> pd.Series:
    if hydro.empty:
        return pd.Series(dtype=str)
    return hydro["quality_flag"].astype(str)


def build_training_matrix_hydrocore() -> pd.DataFrame:
    labels = _read_gold("doc_labels_gold.csv")
    discharge = _read_gold("daily_discharge_gold.csv")
    hydro = _read_gold("daily_hydroclimate_gold.csv")
    if labels.empty:
        out = pd.DataFrame()
        _write_csv(out, _gold_path("training_matrix_hydrocore.csv"))
        return out
    labels = labels.copy()
    labels["date"] = _date(labels["date"]).dt.date.astype(str)
    labels["DOC_mgC_L"] = _num(labels["value_mgC_L"])
    base_cols = [
        "label_id",
        "river",
        "station",
        "date",
        "year",
        "doy",
        "DOC_mgC_L",
        "source_id",
        "quality_flag",
        "provenance_tier",
        "usability_tier",
    ]
    out = labels[base_cols].rename(columns={"source_id": "source_id_label", "quality_flag": "quality_flag_label"})
    if not discharge.empty:
        d = discharge[["river", "date", "Q_m3s", "source_id", "quality_flag"]].rename(columns={"source_id": "source_id_discharge", "quality_flag": "quality_flag_discharge"})
        out = out.merge(d, on=["river", "date"], how="left")
    if not hydro.empty:
        h = hydro[["river", "date", "temperature_2m_C", "positive_degree_day_Cday", "snow_cover_fraction", "snow_depletion_rate_7d", "surface_runoff_m", "source_id_temperature", "quality_flag"]].rename(columns={"source_id_temperature": "source_id_hydroclimate", "quality_flag": "quality_flag_hydroclimate"})
        out = out.merge(h, on=["river", "date"], how="left")
    out["date_dt"] = _date(out["date"])
    out["doy"] = pd.to_numeric(out["doy"], errors="coerce").fillna(out["date_dt"].dt.dayofyear)
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 366.0)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 366.0)
    ordered = [
        "label_id",
        "river",
        "station",
        "date",
        "year",
        "doy",
        "DOC_mgC_L",
        "Q_m3s",
        "sin_doy",
        "cos_doy",
        "temperature_2m_C",
        "positive_degree_day_Cday",
        "snow_cover_fraction",
        "snow_depletion_rate_7d",
        "surface_runoff_m",
        "source_id_label",
        "source_id_discharge",
        "source_id_hydroclimate",
        "quality_flag_label",
        "quality_flag_discharge",
        "quality_flag_hydroclimate",
        "provenance_tier",
        "usability_tier",
    ]
    out = out[[col for col in ordered if col in out.columns]].sort_values(["river", "date", "label_id"])
    _write_csv(out, _gold_path("training_matrix_hydrocore.csv"))
    return out


def build_training_matrix_basin_context() -> pd.DataFrame:
    hydrocore = _read_gold("training_matrix_hydrocore.csv")
    if hydrocore.empty:
        hydrocore = build_training_matrix_hydrocore()
    basin_wide = _read_gold("basin_attributes_curated_wide.csv")
    out = hydrocore.merge(basin_wide, on="river", how="left") if not basin_wide.empty else hydrocore.copy()
    _write_csv(out, _gold_path("training_matrix_basin_context.csv"))
    return out


def build_prediction_grid_daily_hydrocore() -> pd.DataFrame:
    discharge = _read_gold("daily_discharge_gold.csv")
    hydro = _read_gold("daily_hydroclimate_gold.csv")
    if discharge.empty or hydro.empty:
        out = pd.DataFrame()
        _write_csv(out, _gold_path("prediction_grid_daily_hydrocore.csv"))
        return out
    d = discharge[["river", "date", "Q_m3s", "source_id", "quality_flag"]].rename(columns={"source_id": "source_id_discharge", "quality_flag": "quality_flag_discharge"})
    h = hydro[["river", "date", "temperature_2m_C", "positive_degree_day_Cday", "snow_cover_fraction", "snow_depletion_rate_7d", "surface_runoff_m", "source_id_temperature", "quality_flag"]].rename(columns={"source_id_temperature": "source_id_hydroclimate", "quality_flag": "quality_flag_hydroclimate"})
    out = d.merge(h, on=["river", "date"], how="inner")
    out["date_dt"] = _date(out["date"])
    out["year"] = out["date_dt"].dt.year
    out["doy"] = out["date_dt"].dt.dayofyear
    out["sin_doy"] = np.sin(2 * np.pi * out["doy"] / 366.0)
    out["cos_doy"] = np.cos(2 * np.pi * out["doy"] / 366.0)
    ordered = [
        "river",
        "date",
        "year",
        "doy",
        "Q_m3s",
        "sin_doy",
        "cos_doy",
        "temperature_2m_C",
        "positive_degree_day_Cday",
        "snow_cover_fraction",
        "snow_depletion_rate_7d",
        "surface_runoff_m",
        "source_id_discharge",
        "source_id_hydroclimate",
        "quality_flag_discharge",
        "quality_flag_hydroclimate",
    ]
    out = out[ordered].sort_values(["river", "date"])
    _write_csv(out, _gold_path("prediction_grid_daily_hydrocore.csv"))
    return out


def build_prediction_grid_daily_with_basin_context() -> pd.DataFrame:
    grid = _read_gold("prediction_grid_daily_hydrocore.csv")
    if grid.empty:
        grid = build_prediction_grid_daily_hydrocore()
    basin_wide = _read_gold("basin_attributes_curated_wide.csv")
    out = grid.merge(basin_wide, on="river", how="left") if not basin_wide.empty else grid.copy()
    _write_csv(out, _gold_path("prediction_grid_daily_with_basin_context.csv"))
    return out


def _primary_optical() -> pd.DataFrame:
    optical = _read_gold("optical_timeseries_gold.csv")
    if optical.empty:
        return optical
    optical = optical[_bool_series(optical["is_primary_optical_row"])].copy()
    optical["date_dt"] = _date(optical["date"])
    optical["_source_priority"] = optical.apply(lambda row: _source_priority(row.get("source_id", ""), row.get("quality_flag", "")), axis=1)
    optical["_sensor_priority"] = optical["sensor"].apply(_sensor_priority)
    optical["pct_valid_water_pixels"] = _num(optical["pct_valid_water_pixels"])
    return optical


def build_optical_matches_for_window(window: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = _read_gold("doc_labels_gold.csv")
    optical = _primary_optical()
    hydrocore = _read_gold("training_matrix_hydrocore.csv")
    candidate_cols = [
        "label_id",
        "river",
        "sample_date",
        "optical_date",
        "days_offset",
        "abs_days_offset",
        "sensor",
        "collection",
        "image_id",
        "roi_set",
        "source_id",
        "quality_flag",
        *OPTICAL_COLUMNS,
        "n_valid_water_pixels",
        "n_total_pixels",
        "pct_valid_water_pixels",
        "candidate_rank",
        "candidate_selection_reason",
    ]
    if labels.empty or optical.empty:
        candidates = pd.DataFrame(columns=candidate_cols)
        selected = pd.DataFrame()
    else:
        labels = labels[["label_id", "river", "date"]].copy()
        labels["sample_dt"] = _date(labels["date"])
        rows = []
        for river, group in labels.groupby("river"):
            o = optical[optical["river"].astype(str).eq(str(river))].copy()
            if o.empty:
                continue
            for _, label in group.iterrows():
                delta = (o["date_dt"] - label["sample_dt"]).dt.days
                match = o[delta.abs() <= window].copy()
                if match.empty:
                    continue
                match["label_id"] = label["label_id"]
                match["sample_date"] = label["date"]
                match["optical_date"] = match["date"]
                match["days_offset"] = delta.loc[match.index].astype(int)
                match["abs_days_offset"] = match["days_offset"].abs()
                rows.append(match)
        if rows:
            candidates = pd.concat(rows, ignore_index=True)
            candidates = candidates.sort_values(
                ["label_id", "abs_days_offset", "_source_priority", "pct_valid_water_pixels", "_sensor_priority", "image_id"],
                ascending=[True, True, True, False, True, True],
            )
            candidates["candidate_rank"] = candidates.groupby("label_id").cumcount() + 1
            candidates["candidate_selection_reason"] = "nearest_date_then_regenerated_then_valid_pixels_then_sensor_order"
            candidates = candidates.rename(columns={"source_id": "source_id"})
            candidates = candidates[candidate_cols]
            selected = candidates[candidates["candidate_rank"].eq(1)].copy()
        else:
            candidates = pd.DataFrame(columns=candidate_cols)
            selected = pd.DataFrame(columns=candidate_cols)
    _write_csv(candidates, _gold_path(f"optical_match_candidates_{window}d.csv"))
    if selected.empty or hydrocore.empty:
        matrix = pd.DataFrame()
    else:
        optical_selected = selected.rename(columns={"source_id": "source_id_optical", "quality_flag": "quality_flag_optical"})
        base_cols = [
            "label_id",
            "river",
            "date",
            "DOC_mgC_L",
            "Q_m3s",
            "doy",
            "sin_doy",
            "cos_doy",
            "temperature_2m_C",
            "positive_degree_day_Cday",
            "snow_cover_fraction",
            "snow_depletion_rate_7d",
            "surface_runoff_m",
            "source_id_hydroclimate",
            "quality_flag_hydroclimate",
        ]
        matrix = hydrocore[[col for col in base_cols if col in hydrocore.columns]].merge(optical_selected, on=["label_id", "river"], how="inner")
        matrix = matrix[
            [
                "label_id",
                "river",
                "date",
                "DOC_mgC_L",
                "Q_m3s",
                "doy",
                "sin_doy",
                "cos_doy",
                "temperature_2m_C",
                "positive_degree_day_Cday",
                "snow_cover_fraction",
                "snow_depletion_rate_7d",
                "surface_runoff_m",
                "sensor",
                "optical_date",
                "days_offset",
                *OPTICAL_COLUMNS,
                "n_valid_water_pixels",
                "pct_valid_water_pixels",
                "source_id_optical",
                "source_id_hydroclimate",
                "quality_flag_optical",
                "quality_flag_hydroclimate",
            ]
        ]
    _write_csv(matrix, _gold_path(f"training_matrix_optical_matched_{window}d.csv"))
    if window == 3 and not matrix.empty:
        for sensor, suffix in [("HLS", "hls"), ("Sentinel-2", "sentinel2"), ("Landsat", "landsat")]:
            _write_csv(matrix[matrix["sensor"].astype(str).eq(sensor)], _gold_path(f"training_matrix_optical_matched_3d_{suffix}.csv"))
    return candidates, matrix


def build_model_input_matrices() -> None:
    ensure_gold_dirs()
    if not _gold_path("doc_labels_gold.csv").exists():
        build_gold_tables()
    build_training_matrix_hydrocore()
    build_training_matrix_basin_context()
    build_prediction_grid_daily_hydrocore()
    build_prediction_grid_daily_with_basin_context()
    for window in [0, 1, 3, 7]:
        build_optical_matches_for_window(window)
    generate_final_qa_reports()
    generate_data_dictionary()


def _gold_tables() -> list[str]:
    return sorted([p.name for p in GOLD_DIR.glob("*.csv")])


def _hash_rows(table_names: list[str]) -> pd.DataFrame:
    rows = []
    for name in table_names:
        p = _gold_path(name)
        if not p.exists():
            rows.append({"table_name": name, "local_path": relpath(p), "row_count": 0, "sha256": "", "exists": False})
            continue
        try:
            rows_count = sum(1 for _ in p.open("rb")) - 1
        except Exception:
            rows_count = ""
        rows.append({"table_name": name, "local_path": relpath(p), "row_count": rows_count, "sha256": sha256_file(p), "exists": True})
    return pd.DataFrame(rows)


def _source_composition() -> pd.DataFrame:
    rows = []
    for name in _gold_tables():
        frame = _read_gold(name)
        if frame.empty:
            rows.append({"table_name": name, "source_id": "", "rows": 0})
            continue
        source_cols = [col for col in frame.columns if col == "source_id" or col.startswith("source_id_")]
        if not source_cols:
            rows.append({"table_name": name, "source_column": "", "source_id": "no_source_column", "rows": len(frame)})
            continue
        for col in source_cols:
            counts = frame.groupby(col, dropna=False).size().reset_index(name="rows").rename(columns={col: "source_id"})
            for _, row in counts.iterrows():
                rows.append({"table_name": name, "source_column": col, "source_id": row["source_id"], "rows": int(row["rows"])})
    return pd.DataFrame(rows)


def _range_check_rows() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    checks = [
        ("doc_labels_gold.csv", "value_mgC_L", 0, 200),
        ("daily_discharge_gold.csv", "Q_m3s", 0, None),
        ("daily_hydroclimate_gold.csv", "temperature_2m_C", -80, 50),
        ("daily_hydroclimate_gold.csv", "positive_degree_day_Cday", 0, None),
        ("daily_hydroclimate_gold.csv", "snow_cover_fraction", 0, 1),
        ("daily_hydroclimate_gold.csv", "snowmelt_m", 0, None),
        ("daily_hydroclimate_gold.csv", "surface_runoff_m", 0, None),
        ("optical_timeseries_gold.csv", "pct_valid_water_pixels", 0, 1),
    ]
    for table, column, low, high in checks:
        frame = _read_gold(table)
        if frame.empty or column not in frame.columns:
            continue
        values = _num(frame[column])
        bad = values.notna()
        if low is not None:
            bad &= values < low
        if high is not None:
            bad |= values > high
        rows.append({"table_name": table, "column_name": column, "checked_rows": int(values.notna().sum()), "out_of_range_rows": int(bad.sum()), "min_allowed": low, "max_allowed": high, "min_value": values.min(), "max_value": values.max()})
    return pd.DataFrame(rows)


def generate_final_qa_reports() -> pd.DataFrame:
    ensure_gold_dirs()
    issues: list[dict[str, Any]] = []

    def issue(severity: str, table: str, column: str, issue_type: str, description: str, blocking: bool = False, notes: str = "") -> None:
        issues.append(
            {
                "issue_id": f"GOLD-QA-{len(issues)+1:04d}",
                "severity": severity,
                "table_name": table,
                "column_name": column,
                "river": "",
                "date": "",
                "issue_type": issue_type,
                "description": description,
                "blocking_for_gold_freeze": blocking,
                "blocking_for_modeling": blocking,
                "recommended_action": "Open a new freeze only if this is a fatal data bug." if blocking else "Track as non-fatal QA note or sensitivity item.",
                "resolution_status": "open" if blocking else "accepted_non_blocking",
                "notes": notes,
            }
        )

    doc = _read_gold("doc_labels_gold.csv")
    if doc.empty:
        issue("critical", "doc_labels_gold.csv", "", "missing_doc_gold", "DOC gold table is empty.", True)
    else:
        if not doc["parameter_canonical"].astype(str).eq("DOC").all():
            issue("critical", "doc_labels_gold.csv", "parameter_canonical", "toc_or_non_doc_in_doc_gold", "Non-DOC rows found in DOC gold.", True)
        if doc["label_id"].duplicated().any():
            issue("critical", "doc_labels_gold.csv", "label_id", "duplicate_label_id", "Duplicate label_id found.", True)
        if _num(doc["value_mgC_L"]).isna().any():
            issue("critical", "doc_labels_gold.csv", "value_mgC_L", "non_numeric_doc", "DOC value_mgC_L has non-numeric values.", True)

    hydrocore = _read_gold("training_matrix_hydrocore.csv")
    basin_matrix = _read_gold("training_matrix_basin_context.csv")
    for table_name, frame in [("training_matrix_hydrocore.csv", hydrocore), ("training_matrix_basin_context.csv", basin_matrix)]:
        leaked = LAB_FORBIDDEN.intersection(frame.columns)
        if leaked:
            issue("critical", table_name, ";".join(sorted(leaked)), "lab_optical_leakage", "Lab optical columns leaked into production matrix.", True)
    for table_name in ["prediction_grid_daily_hydrocore.csv", "prediction_grid_daily_with_basin_context.csv"]:
        frame = _read_gold(table_name)
        bad_cols = [col for col in frame.columns if col == "DOC_mgC_L" or re.search(r"prediction|pred_doc|flux|TgC|Mg_day", col, re.I)]
        if bad_cols:
            issue("critical", table_name, ";".join(bad_cols), "prediction_grid_leakage", "Prediction grid contains response, prediction, or flux columns.", True)

    basin = _read_gold("basin_context_gold.csv")
    if set(basin.get("river", pd.Series(dtype=str)).astype(str)) != set(RIVERS):
        issue("critical", "basin_context_gold.csv", "river", "missing_basin_river", "Basin context does not cover all six rivers.", True)
    if not basin.empty and basin["quality_flag"].astype(str).str.contains("placeholder|approximate_roi", case=False, na=False).any():
        issue("critical", "basin_context_gold.csv", "quality_flag", "roi_placeholder_basin", "ROI-derived placeholder basin context found.", True)
    if not basin.empty and basin["hydroatlas_attributes_json"].astype(str).isin(["", "{}"]).any():
        issue("high", "basin_context_gold.csv", "hydroatlas_attributes_json", "missing_hydroatlas_attributes", "HydroATLAS attributes missing for at least one river.", False, "Accepted only if explicitly documented; current freeze expects attributes.")

    curated = _read_gold("basin_attributes_curated.csv")
    if curated.empty:
        issue("critical", "basin_attributes_curated.csv", "", "missing_curated_basin_attributes", "Curated basin attributes are empty.", True)
    else:
        bad_predictors = curated[_bool_series(curated["model_use"]) & curated["source_field"].astype(str).isin(ID_TOPOLOGY_FIELDS)]
        if not bad_predictors.empty:
            issue("critical", "basin_attributes_curated.csv", "source_field", "id_topology_predictor", "HydroATLAS ID/topology fields marked as model predictors.", True)

    data_qa = _read_output_table("data_qa_issues.csv")
    if not data_qa.empty:
        current_blockers = data_qa[_bool_series(data_qa.get("blocking_for_full_training", pd.Series(dtype=str))) | _bool_series(data_qa.get("blocking_for_publication", pd.Series(dtype=str)))]
        if not current_blockers.empty:
            issue("medium", "data_qa_issues.csv", "", "historical_or_current_non_gold_issue", f"{len(current_blockers)} non-gold QA blocker rows remain in broader QA table.", False, "Gold freeze uses basin_context_status and superseded failure status.")

    range_checks = _range_check_rows()
    for _, row in range_checks.iterrows():
        if int(row.get("out_of_range_rows", 0) or 0) > 0:
            issue(
                "low",
                str(row.get("table_name", "")),
                str(row.get("column_name", "")),
                "range_check_flag",
                f"{int(row['out_of_range_rows'])} rows are outside the configured screening range.",
                False,
                "Flagged for review; not a gold freeze blocker unless confirmed as a fatal data bug.",
            )

    issue_frame = pd.DataFrame(issues)
    if issue_frame.empty:
        issue_frame = pd.DataFrame(columns=["issue_id", "severity", "table_name", "column_name", "river", "date", "issue_type", "description", "blocking_for_gold_freeze", "blocking_for_modeling", "recommended_action", "resolution_status", "notes"])
    _write_csv(issue_frame, GOLD_TABLE_DIR / "final_data_qa_issues.csv")

    null_rows = []
    for name in _gold_tables():
        frame = _read_gold(name)
        for col in frame.columns:
            null_rows.append({"table_name": name, "column_name": col, "rows": len(frame), "null_or_blank_rows": int(frame[col].isna().sum() + frame[col].astype(str).eq("").sum()), "null_or_blank_rate": float((frame[col].isna() | frame[col].astype(str).eq("")).mean()) if len(frame) else 0})
    _write_csv(pd.DataFrame(null_rows), GOLD_TABLE_DIR / "final_null_rate_by_table.csv")
    _write_csv(range_checks, GOLD_TABLE_DIR / "final_range_checks.csv")
    dup_rows = []
    for name, keys in [
        ("doc_labels_gold.csv", ["label_id"]),
        ("daily_discharge_gold.csv", ["river", "date"]),
        ("daily_hydroclimate_gold.csv", ["river", "date"]),
        ("basin_context_gold.csv", ["river"]),
    ]:
        frame = _read_gold(name)
        dup_rows.append({"table_name": name, "keys": ";".join(keys), "duplicate_rows": int(frame.duplicated(keys).sum()) if not frame.empty and set(keys).issubset(frame.columns) else 0})
    _write_csv(pd.DataFrame(dup_rows), GOLD_TABLE_DIR / "final_duplicate_checks.csv")
    _write_csv(_source_composition(), GOLD_TABLE_DIR / "final_source_composition.csv")
    count_rows = [{"table_name": name, "rows": len(_read_gold(name))} for name in _gold_tables()]
    _write_csv(pd.DataFrame(count_rows), GOLD_TABLE_DIR / "final_matrix_row_counts.csv")

    lines = [
        "# Final Data Cleaning Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## QA Issues",
        _md_table(issue_frame, max_rows=200),
        "",
        "## Null Rates",
        "See `outputs/tables/gold/final_null_rate_by_table.csv`.",
        "",
        "## Range Checks",
        _md_table(range_checks),
    ]
    (GOLD_REPORT_DIR / "final_data_cleaning_report.md").write_text("\n".join(lines), encoding="utf-8")
    return issue_frame


def _column_description(table: str, column: str) -> dict[str, Any]:
    can_response = column == "DOC_mgC_L"
    is_identifier = column in {"label_id", "river", "station", "date", "sample_id", "basin_id", "pfaf_id", "image_id"} or column.upper() in ID_TOPOLOGY_FIELDS
    is_quality = "quality" in column or column in {"provenance_tier", "usability_tier", "notes", "source_id", "source_id_label", "source_id_discharge", "source_id_hydroclimate", "source_id_optical"}
    can_predict = False
    if table.startswith("training_matrix") or table.startswith("prediction_grid"):
        can_predict = not can_response and not is_identifier and not is_quality and column not in LAB_FORBIDDEN and not re.search(r"prediction|flux", column, re.I)
    if column in OPTICAL_COLUMNS:
        can_predict = table.startswith("training_matrix_optical")
    if column.startswith("basin_"):
        can_predict = table in {"training_matrix_basin_context.csv", "prediction_grid_daily_with_basin_context.csv"}
    if column in LAB_FORBIDDEN:
        can_predict = False
    unit = ""
    if column in {"DOC_mgC_L"}:
        unit = "mg C/L"
    elif column == "Q_m3s":
        unit = "m3/s"
    elif column.endswith("_m"):
        unit = "m"
    elif column.endswith("_C") or column == "positive_degree_day_Cday":
        unit = "C or C-day"
    elif column in {"sin_doy", "cos_doy", "snow_cover_fraction", "pct_valid_water_pixels"}:
        unit = "unitless"
    return {
        "description": column.replace("_", " "),
        "unit": unit,
        "can_be_model_predictor": can_predict,
        "can_be_response": can_response,
        "is_identifier": is_identifier,
        "is_quality_field": is_quality,
    }


def generate_data_dictionary() -> pd.DataFrame:
    ensure_gold_dirs()
    rows = []
    for name in _gold_tables():
        frame = _read_gold(name)
        for col in frame.columns:
            meta = _column_description(name, col)
            rows.append(
                {
                    "table_name": name,
                    "column_name": col,
                    "dtype": str(frame[col].dtype),
                    "description": meta["description"],
                    "unit": meta["unit"],
                    "allowed_values": "",
                    "source_table": "canonical_or_gold_derived",
                    "source_column": col,
                    "can_be_model_predictor": meta["can_be_model_predictor"],
                    "can_be_response": meta["can_be_response"],
                    "is_identifier": meta["is_identifier"],
                    "is_quality_field": meta["is_quality_field"],
                    "notes": "Gold data dictionary generated automatically; see gold reports for table-level rules.",
                }
            )
    dictionary = pd.DataFrame(rows)
    _write_csv(dictionary, GOLD_TABLE_DIR / "data_dictionary_gold.csv")
    lines = [
        "# Gold Data Dictionary",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "DOC is the response only. Lab absorbance/CDOM columns are not daily production predictors. Optical bands are predictors only in optical sensitivity matrices. HydroATLAS identifiers/topology fields are identifiers, not predictors.",
        "",
        _md_table(dictionary, max_rows=300),
    ]
    (GOLD_REPORT_DIR / "data_dictionary_gold.md").write_text("\n".join(lines), encoding="utf-8")
    return dictionary


def write_fatal_data_bug_policy() -> Path:
    ensure_gold_dirs()
    text = f"""# Fatal Data Bug Policy

Generated: {utc_now()}

{NO_MODEL_TEXT}

## Fatal Data Bugs

If found, open a new freeze version:

- DOC unit conversion error
- DOC/TOC confusion
- duplicate/preferred label error
- wrong discharge station or unit
- GEE band scaling/mapping error
- station-to-basin catastrophic mismatch
- HydroATLAS aggregation error
- lab optical leakage into daily production predictors
- raw file corrupt/partial
- freeze hash mismatch

## Non-Fatal Issues

Do not reopen this freeze for:

- optional new external source discovered
- additional WQP/DataStream/MDPI candidate rows
- extra optical sensitivity window desired
- additional optional SMAP features
- alternative model feature engineering
- model performance poor

Non-fatal items go to `vNext` or sensitivity appendix, not the current gold freeze.
"""
    out = GOLD_REPORT_DIR / "fatal_data_bug_policy.md"
    out.write_text(text, encoding="utf-8")
    return out


def freeze_gold_data(freeze_id: str) -> Path:
    ensure_gold_dirs()
    build_gold_tables()
    build_model_input_matrices()
    qa = generate_final_qa_reports()
    dictionary = generate_data_dictionary()
    write_fatal_data_bug_policy()
    table_names = _gold_tables()
    hashes = _hash_rows(table_names)
    model_input_names = [name for name in table_names if name.startswith("training_matrix") or name.startswith("prediction_grid")]
    model_hashes = _hash_rows(model_input_names)
    _write_csv(hashes, GOLD_TABLE_DIR / "gold_table_hashes.csv")
    _write_csv(model_hashes, GOLD_TABLE_DIR / "model_input_table_hashes.csv")
    manifest = hashes.copy()
    manifest.insert(0, "freeze_id", freeze_id)
    manifest["generated_at_utc"] = utc_now()
    manifest["git_commit_at_generation"] = _git_commit()
    _write_csv(manifest, GOLD_TABLE_DIR / "data_freeze_gold_manifest.csv")
    source_comp = _source_composition()
    critical = int((qa["severity"].astype(str) == "critical").sum()) if not qa.empty else 0
    high_blocking = int(((qa["severity"].astype(str) == "high") & _bool_series(qa["blocking_for_gold_freeze"])).sum()) if not qa.empty else 0
    tests_passed, test_summary = _run_pytest_for_gold()
    (GOLD_REPORT_DIR / "test_report_gold.md").write_text(
        "# Gold Test Report\n\n"
        f"Generated: {utc_now()}\n\n"
        f"{NO_MODEL_TEXT}\n\n"
        "## Result\n\n"
        "```text\n"
        f"{test_summary}\n"
        "```\n",
        encoding="utf-8",
    )
    lines = [
        "# Gold Data Freeze Report",
        "",
        f"freeze_id: `{freeze_id}`",
        f"generated_at_utc: `{utc_now()}`",
        f"git_commit_at_generation: `{_git_commit()}`",
        "input_freeze_id: `data_freeze_20260526_v3`",
        "",
        NO_MODEL_TEXT,
        "",
        "Future modeling should read only `data/processed/gold/*`.",
        "",
        "## Readiness Flags",
        f"- GOLD_FREEZE_READY: `{critical == 0 and high_blocking == 0 and tests_passed}`",
        f"- QA_CRITICAL_ISSUES: `{critical}`",
        f"- QA_HIGH_BLOCKING_ISSUES: `{high_blocking}`",
        f"- TESTS_PASSED: `{tests_passed}`",
        "",
        "## Gold Table Hashes",
        _md_table(hashes, max_rows=300),
        "",
        "## Model Input Matrix Hashes",
        _md_table(model_hashes, max_rows=300),
        "",
        "## Source Composition",
        _md_table(source_comp, max_rows=300),
        "",
        "## QA Summary",
        _md_table(qa, max_rows=200),
        "",
        "## Data Dictionary",
        f"- rows: `{len(dictionary)}`",
        "- report: `outputs/reports/gold/data_dictionary_gold.md`",
        "",
        "## Fatal Data Bug Policy Summary",
        "Open a new freeze version only for fatal data bugs such as DOC/TOC confusion, unit conversion errors, duplicate/preferred label errors, GEE band mapping errors, basin aggregation errors, lab optical leakage, corrupt raw files, or hash mismatches.",
    ]
    out = GOLD_REPORT_DIR / "data_freeze_gold_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _run_pytest_for_gold() -> tuple[bool, str]:
    try:
        result = subprocess.run([sys.executable, "-m", "pytest"], cwd=path(), text=True, capture_output=True, timeout=1800)
        output = (result.stdout + "\n" + result.stderr).strip()
        summary = output.splitlines()[-1] if output else f"pytest exited {result.returncode}"
        return result.returncode == 0, summary
    except Exception as exc:
        return False, str(exc)
