from __future__ import annotations

from pathlib import Path

import pandas as pd

from .manifest import FILE_MANIFEST_PATH, SOURCE_REGISTRY_PATH, read_manifest
from .normalize import load_rivers
from .paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs
from .schemas import empty_table, read_table_if_exists


def _read_processed(table_name: str) -> pd.DataFrame:
    try:
        return read_table_if_exists(table_name)
    except Exception:
        return empty_table(table_name)


def _read_output_table(file_name: str) -> pd.DataFrame:
    table_path = TABLE_DIR / file_name
    if not table_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(table_path).fillna("")
    except Exception:
        return pd.DataFrame()


def _md_table(frame: pd.DataFrame, max_rows: int = 500) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def _count_table(frame: pd.DataFrame, group_cols: list[str], value_name: str = "count") -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=group_cols + [value_name])
    return frame.groupby(group_cols, dropna=False).size().reset_index(name=value_name)


def _real_exclusions(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty or "exclusion_reason" not in labels.columns:
        return pd.DataFrame(columns=list(labels.columns) if not labels.empty else ["river", "exclusion_reason"])
    out = labels.copy()
    reason = out["exclusion_reason"].fillna("").astype(str).str.strip()
    valid = (reason != "") & ~reason.str.lower().isin({"nan", "none", "<na>", "nat"})
    out = out.loc[valid].copy()
    out["exclusion_reason"] = reason.loc[valid]
    return out


def _download_summary(manifest: pd.DataFrame) -> pd.DataFrame:
    if manifest.empty:
        return pd.DataFrame(columns=["source_id", "download_status", "file_count", "failure_reason"])
    return (
        manifest.groupby(["source_id", "download_status", "failure_reason"], dropna=False)
        .size()
        .reset_index(name="file_count")
        .sort_values(["source_id", "download_status"])
    )


def _label_summary(canonical: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rivers = list(load_rivers())
    for river in rivers:
        raw_count = int((raw["raw_river"].astype(str).str.replace("'", "", regex=False).str.lower().str.contains(river.lower(), na=False)).sum()) if not raw.empty else 0
        group = canonical[canonical["river"] == river] if not canonical.empty else pd.DataFrame()
        tiers = group["usability_tier"].value_counts().to_dict() if not group.empty else {}
        rows.append(
            {
                "river": river,
                "raw_count": raw_count,
                "canonical_count": len(group),
                "Tier_A": int(tiers.get("A", 0)),
                "Tier_B": int(tiers.get("B", 0)),
                "Tier_C": int(tiers.get("C", 0)),
                "Tier_D": int(tiers.get("D", 0)),
                "can_train_doc_model": int(group["can_train_doc_model"].astype(str).str.lower().isin(["true", "1"]).sum()) if not group.empty else 0,
                "can_train_daily_flux_model": int(group["can_train_daily_flux_model"].astype(str).str.lower().isin(["true", "1"]).sum()) if not group.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def _coverage(frame: pd.DataFrame, date_col: str, value_col: str | None = None) -> pd.DataFrame:
    if frame.empty or date_col not in frame.columns:
        return pd.DataFrame(columns=["river", "first_date", "last_date", "n_days", "n_nonmissing"])
    temp = frame.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    rows = []
    for river, group in temp.groupby("river", dropna=False):
        valid_dates = group[date_col].dropna()
        rows.append(
            {
                "river": river,
                "first_date": valid_dates.min().date().isoformat() if not valid_dates.empty else "",
                "last_date": valid_dates.max().date().isoformat() if not valid_dates.empty else "",
                "n_days": int(valid_dates.nunique()),
                "n_nonmissing": int(group[value_col].notna().sum()) if value_col and value_col in group.columns else len(group),
            }
        )
    return pd.DataFrame(rows).sort_values("river")


def _optical_match_counts(labels: pd.DataFrame, optical: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if labels.empty:
        return pd.DataFrame(columns=["river", "window_days", "matched_doc_samples"])
    for river in load_rivers():
        label_dates = pd.to_datetime(labels[(labels["river"] == river) & (labels["parameter_canonical"] == "DOC")]["date"], errors="coerce").dropna()
        optical_dates = pd.to_datetime(optical[optical["river"] == river]["date"], errors="coerce").dropna() if not optical.empty else pd.Series(dtype="datetime64[ns]")
        for window in [0, 1, 3, 7]:
            matched = 0
            for date in label_dates:
                if not optical_dates.empty and (abs((optical_dates - date).dt.days) <= window).any():
                    matched += 1
            rows.append({"river": river, "window_days": window, "matched_doc_samples": matched})
    return pd.DataFrame(rows)


def _old_snapshot_breakdown(inventory: pd.DataFrame) -> pd.DataFrame:
    if inventory.empty:
        return pd.DataFrame(columns=["old_project_subdir", "file_count"])
    out = inventory.groupby("old_project_subdir", dropna=False).size().reset_index(name="file_count")
    total = pd.DataFrame([{"old_project_subdir": "total", "file_count": int(out["file_count"].sum())}])
    return pd.concat([out, total], ignore_index=True)


def _old_snapshot_promotable(inventory: pd.DataFrame) -> pd.DataFrame:
    if inventory.empty:
        return pd.DataFrame(columns=["product_family", "file_count", "target_canonical_table"])
    promotable = inventory[inventory["promotable_to_canonical"].astype(str).str.lower().isin(["true", "1"])]
    if promotable.empty:
        return pd.DataFrame(columns=["product_family", "file_count", "target_canonical_table"])
    return (
        promotable.groupby(["inferred_product_family", "target_canonical_table"], dropna=False)
        .size()
        .reset_index(name="file_count")
        .rename(columns={"inferred_product_family": "product_family"})
        .sort_values(["product_family", "target_canonical_table"])
    )


def _source_composition(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    old_source = "old_arctic_doc_snowmelt_untrained_data"
    for table_name, frame in tables.items():
        if frame.empty or "source_id" not in frame.columns:
            rows.append({"canonical_table": table_name, "source_id": "", "rows": 0})
            rows.append({"canonical_table": table_name, "source_id": old_source, "rows": 0})
            continue
        counts = frame.groupby("source_id", dropna=False).size().reset_index(name="rows")
        seen = set()
        for _, row in counts.iterrows():
            seen.add(str(row["source_id"]))
            rows.append({"canonical_table": table_name, "source_id": row["source_id"], "rows": int(row["rows"])})
        if old_source not in seen:
            rows.append({"canonical_table": table_name, "source_id": old_source, "rows": 0})
    return pd.DataFrame(rows)


def generate_data_availability_report() -> Path:
    ensure_project_dirs()
    manifest = read_manifest()
    raw = _read_processed("doc_labels_raw")
    labels = _read_processed("doc_labels_canonical")
    absorbance = _read_processed("lab_optical_proxy_canonical")
    discharge = _read_processed("daily_discharge_canonical")
    hydro = _read_processed("daily_hydroclimate_canonical")
    optical = _read_processed("optical_timeseries_canonical")
    roi = _read_processed("roi_catalog")
    auxiliary = _read_processed("auxiliary_context_canonical")
    matrix = _read_processed("training_matrix_daily_predictable")
    inventory = _read_output_table("old_snapshot_inventory.csv")
    raw_compare = _read_output_table("old_snapshot_raw_compare.csv")
    promotion = _read_output_table("old_snapshot_promotion_summary.csv")
    hydro_unmapped = _read_output_table("old_snapshot_hydroclimate_unmapped_columns.csv")
    candidate_summary = _read_output_table("candidate_label_audit_summary.csv")
    candidate_final = _read_output_table("candidate_source_final_status.csv")
    basin_status = _read_output_table("basin_context_status.csv")
    if basin_status.empty:
        basin_status = _read_output_table("hydrobasins_hydroatlas_acquisition_status.csv")
    gee_plan = _read_output_table("gee_extraction_plan.csv")
    gee_status = _read_output_table("gee_regeneration_status.csv")
    gee_final_status = _read_output_table("gee_regeneration_final_status.csv")
    data_qa_issues = _read_output_table("data_qa_issues.csv")
    source_priority = _read_output_table("source_priority_audit.csv")

    report = [
        "# Data Availability Report",
        "",
        "This report audits data acquisition and preprocessing readiness only. No DOC model was trained.",
        "",
        "## 1. Download Status Summary",
        _md_table(_download_summary(manifest)),
        "",
        "## 2. Source-Level Files, Status, and Failures",
        _md_table(_download_summary(manifest)),
        "",
        "## 3. DOC Label Counts by River",
        _md_table(_label_summary(labels, raw)),
        "",
        "## 4. DOC Label Counts by River and Year",
        _md_table(_count_table(labels[labels["parameter_canonical"] == "DOC"] if not labels.empty else labels, ["river", "year"], "doc_label_count")),
        "",
        "## 5. Absorbance/CDOM Pair Counts by River",
        _md_table(_count_table(absorbance, ["river"], "lab_optical_rows")),
        "",
        "## 6. Daily Discharge Coverage",
        _md_table(_coverage(discharge, "date", "Q_m3s")),
        "",
        "## 7. Hydroclimate Daily Coverage",
        _md_table(_coverage(hydro, "date")),
        "",
        "## 8. Optical Proxy Coverage by Sensor",
        _md_table(_count_table(optical, ["river", "sensor"], "optical_rows")),
        "",
        "## 9. Optical Matched DOC Sample Count",
        _md_table(_optical_match_counts(labels, optical)),
        "",
        "## Old Project Snapshot Breakdown",
        _md_table(_old_snapshot_breakdown(inventory)),
        "",
        "## Old Snapshot Promotable Files",
        _md_table(_old_snapshot_promotable(inventory)),
        "",
        "## Old Snapshot Promotion Summary",
        _md_table(promotion),
        "",
        "## Old Snapshot Raw Duplicate/Conflict Summary",
        _md_table(_count_table(raw_compare, ["decision"], "file_count") if not raw_compare.empty else raw_compare),
        "",
        "## Old Snapshot ROI Promotion Summary",
        _md_table(_count_table(roi[roi["source_id"] == "old_arctic_doc_snowmelt_untrained_data"] if not roi.empty and "source_id" in roi.columns else roi, ["river", "roi_set"], "roi_count")),
        "",
        "## Old Snapshot Hydroclimate Promotion Summary",
        _md_table(_coverage(hydro[hydro["source_id"] == "old_arctic_doc_snowmelt_untrained_data"] if not hydro.empty and "source_id" in hydro.columns else hydro, "date")),
        "",
        "## Old Snapshot Optical Promotion Summary",
        _md_table(_count_table(optical[optical["source_id"] == "old_arctic_doc_snowmelt_untrained_data"] if not optical.empty and "source_id" in optical.columns else optical, ["river", "sensor"], "optical_rows")),
        "",
        "## Canonical Tables Source Composition",
        _md_table(_source_composition({
            "doc_labels_canonical": labels,
            "daily_hydroclimate_canonical": hydro,
            "optical_timeseries_canonical": optical,
            "roi_catalog": roi,
            "auxiliary_context_canonical": auxiliary,
        })),
        "",
        "## Remaining Snapshot Files Not Promoted",
        _md_table(inventory[inventory["promotable_to_canonical"].astype(str).str.lower().isin(["false", "0", ""])][["snapshot_path", "inferred_product_family", "not_promoted_reason"]] if not inventory.empty else inventory),
        "",
        "## Old Snapshot Hydroclimate Unmapped Columns",
        _md_table(hydro_unmapped),
        "",
        "## 10. Duplicate Statistics and Rules",
        "Deduplication groups records by river, station, date, parameter, and sample id when available. Preference order is official ArcticGRO current, accepted/non-flagged records, explicit DOC, complete coordinates, and newest version.",
        "",
        _md_table(_count_table(labels, ["is_duplicate", "preferred_record"], "records")),
        "",
        "## 11. Unavailable Records and Exclusion Reasons",
        _md_table(_count_table(_real_exclusions(labels), ["river", "exclusion_reason"], "records")),
        "",
        "## 12. Future Training Recommendations",
        "- Recommended main training set: `training_matrix_daily_predictable.csv`, daily-predictable features only.",
        "- Recommended supplementary validation: `lab_optical_proxy_canonical.csv` for absorbance/CDOM mechanism checks.",
        "- Recommended optical sensitivity: HLS/Sentinel-2/Landsat matched subsets once `optical_timeseries_canonical.csv` is populated.",
        "",
        "## Data Completion Candidate Label Audit",
        _md_table(candidate_summary),
        "",
        "## Candidate Source Final Status",
        _md_table(candidate_final),
        "",
        "## Basin Context Acquisition Status",
        _md_table(basin_status),
        "",
        "## GEE Extraction Plan Summary",
        _md_table(_count_table(gee_plan, ["source_id", "estimated_output_table", "needs_regeneration"], "planned_tasks") if not gee_plan.empty else gee_plan),
        "",
        "## GEE Regeneration Status",
        _md_table(gee_status),
        "",
        "## GEE Regeneration Final Status",
        _md_table(gee_final_status),
        "",
        "## Data QA Issues",
        _md_table(data_qa_issues),
        "",
        "## Source Priority Audit",
        _md_table(source_priority),
        "",
        "## 13. Explicit Warnings",
        "- Do not use lab absorbance as production daily predictor.",
        "- Do not treat satellite reflectance as direct DOC observation.",
        "- Do not treat six-river domain as full Arctic Ocean DOC budget.",
        "- Do not silently merge TOC with DOC.",
        "",
        "## Generated Tables",
        f"- Training matrix rows: {len(matrix)}",
    ]
    out = REPORT_DIR / "data_availability_report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    return out


def generate_provenance_report() -> Path:
    ensure_project_dirs()
    manifest = read_manifest()
    labels = _read_processed("doc_labels_canonical")
    absorbance = _read_processed("lab_optical_proxy_canonical")
    discharge = _read_processed("daily_discharge_canonical")
    hydro = _read_processed("daily_hydroclimate_canonical")
    optical = _read_processed("optical_timeseries_canonical")
    basin = _read_processed("basin_context_canonical")
    roi = _read_processed("roi_catalog")
    auxiliary = _read_processed("auxiliary_context_canonical")
    inventory = _read_output_table("old_snapshot_inventory.csv")
    raw_compare = _read_output_table("old_snapshot_raw_compare.csv")
    promotion = _read_output_table("old_snapshot_promotion_summary.csv")
    candidate_summary = _read_output_table("candidate_label_audit_summary.csv")
    candidate_final = _read_output_table("candidate_source_final_status.csv")
    basin_status = _read_output_table("basin_context_status.csv")
    gee_status = _read_output_table("gee_regeneration_status.csv")
    gee_final_status = _read_output_table("gee_regeneration_final_status.csv")
    source_priority_policy = _read_output_table("source_priority_policy.csv")
    training_source_audit = _read_output_table("training_matrix_source_audit.csv")
    freeze_hashes = _read_output_table("data_freeze_canonical_hashes.csv")
    tables = {
        "doc_labels_canonical": labels,
        "lab_optical_proxy_canonical": absorbance,
        "daily_discharge_canonical": discharge,
        "daily_hydroclimate_canonical": hydro,
        "optical_timeseries_canonical": optical,
        "basin_context_canonical": basin,
        "roi_catalog": roi,
        "auxiliary_context_canonical": auxiliary,
    }
    lines = [
        "# Provenance Report",
        "",
        "Every canonical table is expected to retain source_id, source file/sheet/row information in `notes`, or source-specific provenance columns.",
        "",
        "## Source Files, Versions, and SHA256",
        _md_table(manifest[["source_id", "local_path", "file_name", "sha256", "version_detected", "download_status", "retrieved_at_utc"]] if not manifest.empty else manifest),
        "",
        "## Canonical Table Sources",
    ]
    for name, frame in tables.items():
        lines.append(f"### {name}")
        if frame.empty:
            lines.append("_No rows._")
            lines.append("")
            continue
        if "source_id" in frame.columns:
            lines.append(_md_table(_count_table(frame, ["source_id"], "rows")))
        else:
            lines.append("_No source_id column._")
        lines.append("")

    lines.extend(
        [
            "## Deduplication Preference",
            "DOC labels prefer official ArcticGRO current, accepted/non-flagged records, explicit DOC, complete station metadata, and newer dataset versions. Duplicate decisions are written to `outputs/tables/duplicate_decisions.csv`.",
            "",
            "## Unit Conversion",
            "DOC/TOC values in `mg/L`, `mg C/L`, `mg/L as C`, `ug/L`, `ug C/L`, and `ug/L as C` are normalized to `value_mgC_L`. Invalid or unclear units are excluded or Tier D flagged.",
            "",
            "## Candidate-Only Sources",
            "WQP/USGS Yukon, DataStream Mackenzie, PARTNERS/MDPI supplements, and Arctic Data Center Tank 2023 are candidate/benchmark sources until duplicate, site, method, medium, fraction, and provenance audits are complete.",
            "",
            "## Scientific Boundary",
            "Lab absorbance/CDOM supports mechanism validation only by default. Satellite reflectance remains optical proxy data, never DOC labels.",
            "",
            "## Old Snapshot Audit and Promotion",
            "Old snapshot files are audited from `old_arctic_doc_snowmelt_untrained_data`. Raw ArcticGRO files are compared to current official downloads and are not directly promoted. Legacy ROI, hydroclimate, HLS optical proxy, and auxiliary context rows are marked with legacy quality flags and snapshot provenance.",
            "",
            "### Old Snapshot Breakdown",
            _md_table(_old_snapshot_breakdown(inventory)),
            "",
        "### Old Snapshot Promotion Summary",
        _md_table(promotion),
        "",
        "### Candidate Label Audit Summary",
        _md_table(candidate_summary),
        "",
        "### Candidate Source Final Status",
        _md_table(candidate_final),
        "",
        "### Basin Context Status",
        _md_table(basin_status),
        "",
        "### GEE Regeneration Status",
        _md_table(gee_status),
        "",
        "### GEE Regeneration Final Status",
        _md_table(gee_final_status),
        "",
        "### Source Priority Policy",
        _md_table(source_priority_policy),
        "",
        "### Training Matrix Source Audit",
        _md_table(training_source_audit),
        "",
        "### Data Freeze Canonical Hashes",
        _md_table(freeze_hashes),
        "",
        "### Old Snapshot Raw Decisions",
            _md_table(_count_table(raw_compare, ["decision"], "file_count") if not raw_compare.empty else raw_compare),
            "",
            "### Canonical Tables Source Composition",
            _md_table(_source_composition(tables)),
        ]
    )
    out = REPORT_DIR / "provenance_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def generate_reports() -> tuple[Path, Path]:
    return generate_data_availability_report(), generate_provenance_report()
