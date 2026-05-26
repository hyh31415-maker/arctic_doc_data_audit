from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .manifest import read_manifest, utc_now
from .normalize import load_rivers
from .paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs
from .schemas import read_table_if_exists


LEGACY_SOURCE = "old_arctic_doc_snowmelt_untrained_data"
NO_MODEL_TEXT = "No DOC model was trained. No DOC prediction or flux product was generated."
GEE_EXPECTATIONS = {
    "gee_hls_s30_l30": {"source": "hls", "sensor": "HLS", "years": "2016-2025", "expected_chunks": 60, "publication_required": True},
    "gee_sentinel2_sr_harmonized": {"source": "sentinel2", "sensor": "Sentinel-2", "years": "2017-2025", "expected_chunks": 54, "publication_required": True},
    "gee_landsat_c2_l2": {"source": "landsat_c2", "sensor": "Landsat", "years": "2003-2025", "expected_chunks": 138, "publication_required": True},
    "gee_era5_land": {"source": "era5_land", "sensor": "ERA5-Land", "years": "2000-2025", "expected_chunks": 156, "publication_required": True},
    "gee_modis_mod10a1": {"source": "modis_snow", "sensor": "MODIS snow", "years": "2000-2025", "expected_chunks": 156, "publication_required": True},
    "gee_smap_context_optional": {"source": "smap", "sensor": "SMAP", "years": "2015-2025", "expected_chunks": 66, "publication_required": False},
}


def _write_csv(frame: pd.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    return destination


def _read_table_file(name: str) -> pd.DataFrame:
    destination = TABLE_DIR / name
    if not destination.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(destination).fillna("")
    except Exception:
        return pd.DataFrame()


def _md_table(frame: pd.DataFrame, max_rows: int = 200) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def source_priority_policy() -> pd.DataFrame:
    rows = [
        {"data_family": "daily_hydroclimate", "priority": 1, "source_rule": "quality_flag=regenerated_gee or source_id startswith gee_", "applies_to": "training_matrix_daily_predictable", "notes": "Use regenerated GEE predictor values when present."},
        {"data_family": "daily_hydroclimate", "priority": 2, "source_rule": f"source_id={LEGACY_SOURCE}", "applies_to": "training_matrix_daily_predictable", "notes": "Legacy snapshot predictors are backup/reference only."},
        {"data_family": "daily_hydroclimate", "priority": 3, "source_rule": "missing", "applies_to": "training_matrix_daily_predictable", "notes": "Leave predictor missing; do not fabricate values."},
        {"data_family": "optical_matching", "priority": 1, "source_rule": "sensor-specific regenerated GEE row", "applies_to": "optical match flags and source audit", "notes": "Prefer regenerated HLS/Sentinel-2/Landsat matches."},
        {"data_family": "optical_matching", "priority": 2, "source_rule": f"sensor-specific {LEGACY_SOURCE} row", "applies_to": "optical match flags and source audit", "notes": "Legacy optical rows are backup/reference."},
        {"data_family": "optical_matching", "priority": 3, "source_rule": "no optical", "applies_to": "optical match flags and source audit", "notes": "Do not require optical for all DOC labels."},
    ]
    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "source_priority_policy.csv")
    return frame


def _priority(frame: pd.DataFrame) -> pd.Series:
    source = frame.get("source_id", pd.Series(index=frame.index, dtype=str)).astype(str)
    quality = frame.get("quality_flag", pd.Series(index=frame.index, dtype=str)).astype(str)
    return quality.eq("regenerated_gee").map({True: 1, False: 2}).where(~source.eq(LEGACY_SOURCE), 2).where(source.ne(""), 3)


def build_training_matrix_source_audit() -> pd.DataFrame:
    matrix = read_table_if_exists("training_matrix_daily_predictable")
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    optical = read_table_if_exists("optical_timeseries_canonical")
    if matrix.empty:
        frame = pd.DataFrame()
        _write_csv(frame, TABLE_DIR / "training_matrix_source_audit.csv")
        return frame

    matrix = matrix.copy()
    matrix["date_dt"] = pd.to_datetime(matrix["date"], errors="coerce")
    if not hydro.empty:
        hydro = hydro.copy()
        hydro["date_dt"] = pd.to_datetime(hydro["date"], errors="coerce")
        hydro["_priority"] = _priority(hydro)
    if not optical.empty:
        optical = optical.copy()
        optical["date_dt"] = pd.to_datetime(optical["date"], errors="coerce")
        optical["_is_regenerated"] = optical["quality_flag"].astype(str).eq("regenerated_gee") | optical["source_id"].astype(str).str.startswith("gee_")

    rows: list[dict[str, Any]] = []
    variables = {
        "temperature_2m_source_id_used": "temperature_2m_C",
        "snow_cover_source_id_used": "snow_cover_fraction",
    }
    for _, row in matrix.iterrows():
        river = str(row.get("river", ""))
        date = row.get("date_dt")
        audit: dict[str, Any] = {
            "label_id": row.get("label_id", ""),
            "river": river,
            "date": row.get("date", ""),
            "hydroclimate_source_id_used": "",
            "temperature_2m_source_id_used": "",
            "snow_cover_source_id_used": "",
            "optical_match_source_priority": "no_optical",
            "has_regenerated_hls_match_3d": False,
            "has_legacy_hls_match_3d": False,
            "has_regenerated_sentinel2_match_3d": False,
            "has_legacy_sentinel2_match_3d": False,
            "has_landsat_match_3d": False,
        }
        if not hydro.empty and pd.notna(date):
            h = hydro[(hydro["river"].astype(str) == river) & (hydro["date_dt"] == date)].sort_values("_priority")
            if not h.empty:
                audit["hydroclimate_source_id_used"] = str(h.iloc[0].get("source_id", ""))
                for out_col, value_col in variables.items():
                    candidates = h[h[value_col].notna() & h[value_col].astype(str).ne("")]
                    if not candidates.empty:
                        audit[out_col] = str(candidates.iloc[0].get("source_id", ""))
        if not optical.empty and pd.notna(date):
            o = optical[(optical["river"].astype(str) == river) & ((optical["date_dt"] - date).dt.days.abs() <= 3)]
            if not o.empty:
                regen = o[o["_is_regenerated"]]
                audit["optical_match_source_priority"] = "regenerated" if not regen.empty else "legacy"
                hls = o[o["sensor"].astype(str).str.contains("HLS", case=False, na=False)]
                s2 = o[o["sensor"].astype(str).str.contains("Sentinel-2", case=False, na=False)]
                landsat = o[o["sensor"].astype(str).str.contains("Landsat", case=False, na=False)]
                audit["has_regenerated_hls_match_3d"] = bool((hls["_is_regenerated"]).any()) if not hls.empty else False
                audit["has_legacy_hls_match_3d"] = bool((~hls["_is_regenerated"]).any()) if not hls.empty else False
                audit["has_regenerated_sentinel2_match_3d"] = bool((s2["_is_regenerated"]).any()) if not s2.empty else False
                audit["has_legacy_sentinel2_match_3d"] = bool((~s2["_is_regenerated"]).any()) if not s2.empty else False
                audit["has_landsat_match_3d"] = bool(not landsat.empty)
        rows.append(audit)
    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "training_matrix_source_audit.csv")
    return frame


def source_priority_audit() -> pd.DataFrame:
    policy = source_priority_policy()
    training = build_training_matrix_source_audit()
    rows = []
    if not training.empty:
        for column in ["hydroclimate_source_id_used", "temperature_2m_source_id_used", "snow_cover_source_id_used", "optical_match_source_priority"]:
            counts = training[column].fillna("").astype(str).value_counts(dropna=False)
            for value, count in counts.items():
                rows.append({"audit_family": column, "source_or_priority": value, "rows": int(count)})
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=["audit_family", "source_or_priority", "rows"])
    _write_csv(frame, TABLE_DIR / "source_priority_audit.csv")
    return frame


def hls_band_mapping_audit() -> pd.DataFrame:
    optical = read_table_if_exists("optical_timeseries_canonical")
    if optical.empty:
        frame = pd.DataFrame(columns=["river", "year", "image_id", "collection", "available_bands_json", "canonical_blue_source", "canonical_green_source", "canonical_red_source", "canonical_nir_source", "canonical_swir1_source", "canonical_swir2_source", "missing_canonical_bands_json", "status", "notes"])
        _write_csv(frame, TABLE_DIR / "gee_hls_band_mapping_audit.csv")
        return frame
    hls = optical[optical["source_id"].astype(str) == "gee_hls_s30_l30"].copy()
    if hls.empty:
        frame = pd.DataFrame()
        _write_csv(frame, TABLE_DIR / "gee_hls_band_mapping_audit.csv")
        return frame
    hls["year"] = pd.to_datetime(hls["date"], errors="coerce").dt.year
    rows = []
    for _, row in hls.drop_duplicates(["river", "year", "image_id", "collection"]).iterrows():
        collection = str(row.get("collection", ""))
        is_l30 = "HLSL30" in collection
        available = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B9", "B10", "B11", "Fmask", "SZA", "SAA", "VZA", "VAA"] if is_l30 else ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B10", "B11", "B12", "Fmask", "SZA", "SAA", "VZA", "VAA"]
        mapping = {
            "blue": "B2",
            "green": "B3",
            "red": "B4",
            "nir": "B5" if is_l30 else "B8A",
            "swir1": "B6" if is_l30 else "B11",
            "swir2": "B7" if is_l30 else "B12",
        }
        missing = [name for name, source in mapping.items() if source not in available]
        rows.append(
            {
                "river": row.get("river", ""),
                "year": int(row.get("year")) if pd.notna(row.get("year")) else "",
                "image_id": row.get("image_id", ""),
                "collection": collection,
                "available_bands_json": json.dumps(available),
                "canonical_blue_source": mapping["blue"],
                "canonical_green_source": mapping["green"],
                "canonical_red_source": mapping["red"],
                "canonical_nir_source": mapping["nir"],
                "canonical_swir1_source": mapping["swir1"],
                "canonical_swir2_source": mapping["swir2"],
                "missing_canonical_bands_json": json.dumps(missing),
                "status": "ok" if not missing else "missing_optional_or_core_bands",
                "notes": "HLS v2/v3 robust band-name audit; B02/B03/B04 are not required.",
            }
        )
    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "gee_hls_band_mapping_audit.csv")
    return frame


def gee_null_value_qc() -> pd.DataFrame:
    rows = []
    optical = read_table_if_exists("optical_timeseries_canonical")
    if not optical.empty:
        expected = ["blue", "green", "red", "nir", "swir1", "swir2", "n_valid_water_pixels", "n_total_pixels"]
        gee = optical[optical["source_id"].astype(str).str.startswith("gee_")]
        for _, row in gee.iterrows():
            year = pd.to_datetime(pd.Series([row.get("date", "")]), errors="coerce").dt.year.iloc[0]
            for variable in expected:
                if variable in row and (pd.isna(row.get(variable)) or str(row.get(variable)).strip() == ""):
                    rows.append({"source_id": row.get("source_id", ""), "river": row.get("river", ""), "year": year if pd.notna(year) else "", "date": row.get("date", ""), "variable": variable, "null_reason": "no_valid_reducer_value_or_optional_band_missing", "fallback_value": "", "quality_flag": row.get("quality_flag", ""), "notes": "Null retained; no Dictionary.set missing-value call is used."})
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    if not hydro.empty:
        expected = ["temperature_2m_C", "precipitation_m", "snow_depth_m", "snowmelt_m", "surface_runoff_m", "subsurface_runoff_m", "total_runoff_m", "positive_degree_day_Cday", "snow_cover_fraction", "snow_depletion_rate_7d"]
        gee = hydro[hydro["source_id"].astype(str).str.startswith("gee_")]
        for _, row in gee.iterrows():
            year = pd.to_datetime(pd.Series([row.get("date", "")]), errors="coerce").dt.year.iloc[0]
            for variable in expected:
                if variable in row and (pd.isna(row.get(variable)) or str(row.get(variable)).strip() == ""):
                    rows.append({"source_id": row.get("source_id", ""), "river": row.get("river", ""), "year": year if pd.notna(year) else "", "date": row.get("date", ""), "variable": variable, "null_reason": "not_provided_by_source_or_no_valid_reducer_value", "fallback_value": "", "quality_flag": row.get("quality_flag", ""), "notes": "Null retained; missing values are recorded rather than failed."})
    frame = pd.DataFrame(rows, columns=["source_id", "river", "year", "date", "variable", "null_reason", "fallback_value", "quality_flag", "notes"])
    _write_csv(frame, TABLE_DIR / "gee_null_value_qc.csv")
    return frame


def gee_failure_audit() -> pd.DataFrame:
    manifest = read_manifest().fillna("")
    summary_rows = []
    for source_id, spec in GEE_EXPECTATIONS.items():
        summary = _read_table_file(f"gee_{spec['source']}_extraction_summary.csv")
        if summary.empty:
            summary = _read_table_file(f"gee_{spec['source'].replace('_snow', '')}_extraction_summary.csv")
        if summary.empty and spec["source"] == "modis_snow":
            summary = _read_table_file("gee_modis_snow_extraction_summary.csv")
        if summary.empty:
            continue
        for _, row in summary.iterrows():
            summary_rows.append(
                {
                    "source_id": source_id,
                    "river": row.get("river", ""),
                    "year": row.get("year", ""),
                    "current_status": row.get("status", ""),
                    "current_failure_reason": row.get("failure_reason", ""),
                    "historical_failure_count": 0,
                    "historical_failure_reason": "",
                    "resolution_status": "current_failure" if str(row.get("failure_reason", "")).strip() else "current_success",
                }
            )
    out = pd.DataFrame(summary_rows)
    failures = manifest[(manifest["source_id"].astype(str).str.startswith("gee_")) & (manifest["failure_reason"].astype(str).str.strip().ne(""))]
    historical_rows = []
    for _, row in failures.iterrows():
        download_url = str(row.get("download_url", ""))
        match = re.match(r"earthengine:([^:]+):([^:]+):([^:]+)", download_url)
        source_name, river, year = (match.group(1), match.group(2), match.group(3)) if match else ("", "", "")
        source_id = str(row.get("source_id", ""))
        superseded = False
        optional_deferred = source_id == "gee_smap_context_optional"
        if not out.empty and river and year:
            current = out[(out["source_id"].astype(str) == source_id) & (out["river"].astype(str) == river) & (out["year"].astype(str) == year)]
            superseded = not current.empty and current["current_status"].astype(str).isin(["downloaded", "empty"]).any()
        if not superseded and not out.empty and "not executed" in str(row.get("failure_reason", "")).lower():
            current_source = out[(out["source_id"].astype(str) == source_id) & (out["current_status"].astype(str).isin(["downloaded", "empty"]))]
            superseded = not current_source.empty
        historical_rows.append(
            {
                "source_id": source_id,
                "river": river,
                "year": year,
                "current_status": "failed_optional_or_deferred" if optional_deferred else ("downloaded_or_empty" if superseded else "historical_failure_no_matching_success"),
                "current_failure_reason": "",
                "historical_failure_count": 1,
                "historical_failure_reason": row.get("failure_reason", ""),
                "resolution_status": "optional_deferred" if optional_deferred else ("superseded_by_successful_regeneration" if superseded else "needs_review"),
            }
        )
    if historical_rows:
        out = pd.concat([out, pd.DataFrame(historical_rows)], ignore_index=True)
    if out.empty:
        out = pd.DataFrame(columns=["source_id", "river", "year", "current_status", "current_failure_reason", "historical_failure_count", "historical_failure_reason", "resolution_status"])
    _write_csv(out, TABLE_DIR / "gee_failure_audit.csv")
    return out


def gee_regeneration_final_status() -> pd.DataFrame:
    rows = []
    optical = read_table_if_exists("optical_timeseries_canonical")
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    for source_id, spec in GEE_EXPECTATIONS.items():
        summary = _read_table_file(f"gee_{spec['source']}_extraction_summary.csv")
        if spec["source"] == "modis_snow":
            summary = _read_table_file("gee_modis_snow_extraction_summary.csv")
        for river in load_rivers():
            source_summary = summary[summary["river"].astype(str) == river] if not summary.empty and "river" in summary.columns else pd.DataFrame()
            successful = int(source_summary["status"].astype(str).isin(["downloaded", "empty"]).sum()) if not source_summary.empty and "status" in source_summary.columns else 0
            failed = int(source_summary["status"].astype(str).eq("failed").sum()) if not source_summary.empty and "status" in source_summary.columns else 0
            failure_reasons = "; ".join(sorted(set(source_summary.get("failure_reason", pd.Series(dtype=str)).dropna().astype(str).str.strip()) - {""})) if not source_summary.empty else ""
            if source_id == "gee_smap_context_optional":
                core = True
                publication = False
                notes = "SMAP is optional and deferred/failed_optional; not a core blocker."
            else:
                if source_id.startswith("gee_") and source_id in {"gee_era5_land", "gee_modis_mod10a1"}:
                    source_rows = hydro[(hydro["source_id"].astype(str) == source_id) & (hydro["river"].astype(str) == river)] if not hydro.empty else pd.DataFrame()
                else:
                    source_rows = optical[(optical["source_id"].astype(str) == source_id) & (optical["river"].astype(str) == river)] if not optical.empty else pd.DataFrame()
                core = not source_rows.empty and failed == 0
                publication = core and failed == 0
                notes = "Regenerated rows present and current extraction summary has no failed chunks." if core else "Missing regenerated rows or current failed chunks remain."
            rows.append(
                {
                    "source_id": source_id,
                    "river": river,
                    "expected_years": spec["years"],
                    "successful_chunks": successful,
                    "failed_chunks": failed,
                    "remaining_failure_reason_summary": failure_reasons,
                    "accepted_for_core_full_training": bool(core),
                    "accepted_for_publication_grade_training": bool(publication),
                    "notes": notes,
                }
            )
    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "gee_regeneration_final_status.csv")
    return frame


def data_qa_issues() -> pd.DataFrame:
    failure_audit = gee_failure_audit()
    priority = source_priority_audit()
    hls_audit = hls_band_mapping_audit()
    null_qc = gee_null_value_qc()
    final_status = gee_regeneration_final_status()
    issues: list[dict[str, Any]] = []
    issue_id = 1

    current_failures = failure_audit[failure_audit["resolution_status"].astype(str) == "current_failure"] if not failure_audit.empty else pd.DataFrame()
    for _, row in current_failures.iterrows():
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "high", "source_id": row.get("source_id", ""), "table_name": "gee_failure_audit", "river": row.get("river", ""), "year": row.get("year", ""), "issue_type": "current_gee_failure", "current_status": row.get("current_status", ""), "recommended_action": "Rerun or manually audit the failed chunk.", "blocking_for_baseline": False, "blocking_for_full_training": True, "blocking_for_publication": True, "notes": row.get("current_failure_reason", "")})
        issue_id += 1

    historical = failure_audit[failure_audit["resolution_status"].astype(str) == "superseded_by_successful_regeneration"] if not failure_audit.empty else pd.DataFrame()
    if not historical.empty:
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "low", "source_id": "gee_*", "table_name": "file_manifest", "river": "", "year": "", "issue_type": "historical_gee_failures_superseded", "current_status": f"{len(historical)} historical failure rows superseded by current successful summaries", "recommended_action": "Keep manifest history; rely on gee_regeneration_final_status for readiness.", "blocking_for_baseline": False, "blocking_for_full_training": False, "blocking_for_publication": False, "notes": "Historical failures include earlier HLS B02 band-name mismatch."})
        issue_id += 1

    basin_status = _read_table_file("basin_context_status.csv")
    basin_value = str(basin_status.iloc[0].get("basin_context_status", "")) if not basin_status.empty else "missing"
    if basin_value != "complete":
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "high", "source_id": "hydrobasins;hydroatlas", "table_name": "basin_context_canonical", "river": "", "year": "", "issue_type": "approximate_basin_context", "current_status": basin_value or "missing", "recommended_action": "Provide real HydroBASINS/HydroATLAS upstream basin files for publication-grade training.", "blocking_for_baseline": False, "blocking_for_full_training": False, "blocking_for_publication": True, "notes": "Approximate ROI context can support core model runs that do not use basin-level attributes."})
        issue_id += 1

    optical = read_table_if_exists("optical_timeseries_canonical")
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    if (not optical.empty and (optical["source_id"].astype(str) == LEGACY_SOURCE).any()) or (not hydro.empty and (hydro["source_id"].astype(str) == LEGACY_SOURCE).any()):
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "medium", "source_id": LEGACY_SOURCE, "table_name": "canonical GEE tables", "river": "", "year": "", "issue_type": "legacy_rows_retained_with_regenerated_rows", "current_status": "legacy rows present", "recommended_action": "Use source_priority_policy and training_matrix_source_audit; keep legacy as reference/backfill only.", "blocking_for_baseline": False, "blocking_for_full_training": False, "blocking_for_publication": False, "notes": "Training matrix prefers regenerated hydroclimate."})
        issue_id += 1

    wqp_failures = read_manifest()
    wqp_failed = wqp_failures[(wqp_failures["source_id"].astype(str) == "wqp_usgs_yukon_candidate") & (wqp_failures["download_status"].astype(str) == "failed")] if not wqp_failures.empty else pd.DataFrame()
    if not wqp_failed.empty:
        discovery_done = (TABLE_DIR / "wqp_characteristic_discovery.csv").exists()
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "low" if discovery_done else "medium", "source_id": "wqp_usgs_yukon_candidate", "table_name": "wqp_usgs_candidate_label_qc", "river": "Yukon", "year": "", "issue_type": "wqp_characteristic_enumeration_rejections", "current_status": f"{len(wqp_failed)} failed historical WQP queries; discovery_completed={discovery_done}", "recommended_action": "Use discovered CharacteristicName values; no default candidate promotion." if discovery_done else "Run discover-wqp-characteristics and use actual returned CharacteristicName values.", "blocking_for_baseline": False, "blocking_for_full_training": False, "blocking_for_publication": False, "notes": "Candidate rows are not promoted by default."})
        issue_id += 1

    smap = final_status[final_status["source_id"].astype(str) == "gee_smap_context_optional"] if not final_status.empty else pd.DataFrame()
    if not smap.empty:
        issues.append({"issue_id": f"QA-{issue_id:04d}", "severity": "optional", "source_id": "gee_smap_context_optional", "table_name": "auxiliary_context_canonical", "river": "", "year": "", "issue_type": "optional_smap_deferred", "current_status": "failed_optional_or_deferred", "recommended_action": "Leave optional unless soil moisture context is needed.", "blocking_for_baseline": False, "blocking_for_full_training": False, "blocking_for_publication": False, "notes": "SMAP is not a critical DOC model predictor."})

    frame = pd.DataFrame(issues, columns=["issue_id", "severity", "source_id", "table_name", "river", "year", "issue_type", "current_status", "recommended_action", "blocking_for_baseline", "blocking_for_full_training", "blocking_for_publication", "notes"])
    _write_csv(frame, TABLE_DIR / "data_qa_issues.csv")
    return frame


def generate_data_qa_report() -> Path:
    ensure_project_dirs()
    issues = data_qa_issues()
    priority = _read_table_file("source_priority_policy.csv")
    priority_audit = _read_table_file("source_priority_audit.csv")
    failure_audit = _read_table_file("gee_failure_audit.csv")
    training_audit = _read_table_file("training_matrix_source_audit.csv")
    hls_audit = _read_table_file("gee_hls_band_mapping_audit.csv")
    null_qc = _read_table_file("gee_null_value_qc.csv")
    final_status = _read_table_file("gee_regeneration_final_status.csv")
    lines = [
        "# Data QA Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Issue Summary",
        _md_table(issues.groupby(["severity", "blocking_for_full_training", "blocking_for_publication"], dropna=False).size().reset_index(name="issues") if not issues.empty else issues),
        "",
        "## Data QA Issues",
        _md_table(issues),
        "",
        "## Source Priority Policy",
        _md_table(priority),
        "",
        "## Source Priority Audit",
        _md_table(priority_audit),
        "",
        "## GEE Failure Audit",
        _md_table(failure_audit),
        "",
        "## GEE Regeneration Final Status",
        _md_table(final_status),
        "",
        "## HLS Band Mapping Audit",
        _md_table(hls_audit),
        "",
        "## GEE Null Value QC",
        _md_table(null_qc),
        "",
        "## Training Matrix Source Audit",
        _md_table(training_audit),
    ]
    out = REPORT_DIR / "data_qa_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def qa_data() -> Path:
    return generate_data_qa_report()


def fix_gee_failures(all_sources: bool = True) -> Path:
    """Rerun only current failed GEE chunks, then refresh QA outputs."""
    failure = gee_failure_audit()
    current = failure[failure["resolution_status"].astype(str) == "current_failure"] if not failure.empty else pd.DataFrame()
    if not current.empty:
        from .gee_regeneration import generate_gee_regeneration_comparison, run_gee_extraction

        source_lookup = {source_id: spec["source"] for source_id, spec in GEE_EXPECTATIONS.items()}
        for _, row in current.drop_duplicates(["source_id", "river", "year"]).iterrows():
            source = source_lookup.get(str(row.get("source_id", "")))
            river = str(row.get("river", ""))
            year = str(row.get("year", ""))
            if not source or not river or not year:
                continue
            if source == "smap":
                continue
            run_gee_extraction(source, river, year, "final_primary")
        generate_gee_regeneration_comparison()
    return generate_data_qa_report()
