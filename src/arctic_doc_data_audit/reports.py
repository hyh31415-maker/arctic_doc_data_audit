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


def _md_table(frame: pd.DataFrame, max_rows: int = 500) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def _count_table(frame: pd.DataFrame, group_cols: list[str], value_name: str = "count") -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=group_cols + [value_name])
    return frame.groupby(group_cols, dropna=False).size().reset_index(name=value_name)


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


def generate_data_availability_report() -> Path:
    ensure_project_dirs()
    manifest = read_manifest()
    raw = _read_processed("doc_labels_raw")
    labels = _read_processed("doc_labels_canonical")
    absorbance = _read_processed("lab_optical_proxy_canonical")
    discharge = _read_processed("daily_discharge_canonical")
    hydro = _read_processed("daily_hydroclimate_canonical")
    optical = _read_processed("optical_timeseries_canonical")
    matrix = _read_processed("training_matrix_daily_predictable")

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
        "## 10. Duplicate Statistics and Rules",
        "Deduplication groups records by river, station, date, parameter, and sample id when available. Preference order is official ArcticGRO current, accepted/non-flagged records, explicit DOC, complete coordinates, and newest version.",
        "",
        _md_table(_count_table(labels, ["is_duplicate", "preferred_record"], "records")),
        "",
        "## 11. Unavailable Records and Exclusion Reasons",
        _md_table(_count_table(labels[labels["exclusion_reason"].astype(str) != ""] if not labels.empty else labels, ["river", "exclusion_reason"], "records")),
        "",
        "## 12. Future Training Recommendations",
        "- Recommended main training set: `training_matrix_daily_predictable.csv`, daily-predictable features only.",
        "- Recommended supplementary validation: `lab_optical_proxy_canonical.csv` for absorbance/CDOM mechanism checks.",
        "- Recommended optical sensitivity: HLS/Sentinel-2/Landsat matched subsets once `optical_timeseries_canonical.csv` is populated.",
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
    tables = {
        "doc_labels_canonical": labels,
        "lab_optical_proxy_canonical": absorbance,
        "daily_discharge_canonical": discharge,
        "daily_hydroclimate_canonical": hydro,
        "optical_timeseries_canonical": optical,
        "basin_context_canonical": basin,
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
        ]
    )
    out = REPORT_DIR / "provenance_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def generate_reports() -> tuple[Path, Path]:
    return generate_data_availability_report(), generate_provenance_report()
