from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .normalize import load_rivers
from .paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs
from .schemas import empty_table, read_table_if_exists


WINDOWS = [0, 1, 3, 7]
HYDRO_PREDICTORS = [
    "temperature_2m_C",
    "positive_degree_day_Cday",
    "snow_cover_fraction",
    "snow_depletion_rate_7d",
    "surface_runoff_m",
]
READINESS_TABLES = [
    "doc_labels_canonical",
    "training_matrix_daily_predictable",
    "daily_discharge_canonical",
    "daily_hydroclimate_canonical",
    "optical_timeseries_canonical",
    "roi_catalog",
]


@dataclass(frozen=True)
class ReadinessOutputs:
    report_path: Path
    by_river_path: Path
    by_year_path: Path
    by_season_window_path: Path


def _read_processed(table_name: str) -> pd.DataFrame:
    try:
        return read_table_if_exists(table_name)
    except Exception:
        return empty_table(table_name)


def _md_table(frame: pd.DataFrame, max_rows: int = 200) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def _read_output_table(name: str) -> pd.DataFrame:
    destination = TABLE_DIR / name
    if not destination.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(destination).fillna("")
    except Exception:
        return pd.DataFrame()


def _bool_series(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])


def _date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _doc_labels(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return labels.copy()
    out = labels[labels["parameter_canonical"].astype(str).str.upper() == "DOC"].copy()
    out["date_dt"] = _date_series(out["date"])
    out["year"] = pd.to_numeric(out.get("year", out["date_dt"].dt.year), errors="coerce")
    return out


def _usable_matrix(matrix: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    out = matrix.copy()
    if out.empty:
        return out
    out["date_dt"] = _date_series(out["date"])
    out["year"] = out["date_dt"].dt.year
    if not labels.empty and "source_id" in labels.columns:
        label_meta = labels[["label_id", "source_id"]].drop_duplicates("label_id")
        out = out.merge(label_meta, on="label_id", how="left")
    else:
        out["source_id"] = pd.NA
    for column in ["Q_m3s", *HYDRO_PREDICTORS]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _has_hydro_predictors(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    available = [column for column in HYDRO_PREDICTORS if column in frame.columns]
    if not available:
        return pd.Series([False] * len(frame), index=frame.index)
    return frame[available].notna().all(axis=1)


def _optical_dates(optical: pd.DataFrame, sensor: str | None) -> dict[str, pd.Series]:
    if optical.empty:
        return {}
    frame = optical.copy()
    if sensor:
        frame = frame[frame["sensor"].astype(str).str.contains(sensor, case=False, na=False)]
    frame["date_dt"] = _date_series(frame["date"])
    frame = frame.dropna(subset=["date_dt"])
    return {
        str(river): group["date_dt"].drop_duplicates().reset_index(drop=True)
        for river, group in frame.groupby("river", dropna=False)
    }


def _match_count(frame: pd.DataFrame, optical_by_river: dict[str, pd.Series], window_days: int) -> int:
    if frame.empty:
        return 0
    matched = 0
    for _, row in frame.iterrows():
        dates = optical_by_river.get(str(row.get("river", "")))
        label_date = row.get("date_dt")
        if dates is None or dates.empty or pd.isna(label_date):
            continue
        if (abs((dates - label_date).dt.days) <= window_days).any():
            matched += 1
    return matched


def _add_optical_counts(row: dict[str, Any], frame: pd.DataFrame, optical: pd.DataFrame) -> None:
    optical_sets = {
        "hls": _optical_dates(optical, "HLS"),
        "sentinel2": _optical_dates(optical, "Sentinel-2"),
        "any_optical": _optical_dates(optical, None),
    }
    for prefix, dates in optical_sets.items():
        for window in WINDOWS:
            row[f"{prefix}_match_{window}d"] = _match_count(frame, dates, window)


def _rate(missing_count: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(missing_count / denominator, 4)


def _predictor_stats(frame: pd.DataFrame) -> dict[str, Any]:
    total = len(frame)
    hydro_complete = _has_hydro_predictors(frame) if not frame.empty else pd.Series(dtype=bool)
    q_complete = frame["Q_m3s"].notna() if "Q_m3s" in frame.columns else pd.Series([False] * len(frame), index=frame.index)
    stats: dict[str, Any] = {
        "labels_with_Q_m3s": int(q_complete.sum()) if not frame.empty else 0,
        "labels_with_hydroclimate_predictors": int(hydro_complete.sum()) if not frame.empty else 0,
        "labels_with_Q_and_hydroclimate_predictors": int((q_complete & hydro_complete).sum()) if not frame.empty else 0,
    }
    stats["missing_Q_m3s_rate"] = _rate(total - stats["labels_with_Q_m3s"], total)
    for column in HYDRO_PREDICTORS:
        nonmissing = int(frame[column].notna().sum()) if column in frame.columns else 0
        stats[f"missing_{column}_rate"] = _rate(total - nonmissing, total)
    return stats


def _roi_summary(roi: pd.DataFrame) -> pd.DataFrame:
    if roi.empty:
        return pd.DataFrame(columns=["river", "roi_count", "manual_review_required_count", "roi_risk_summary"])
    frame = roi.copy()
    manual = _bool_series(frame["manual_review_required"]) if "manual_review_required" in frame.columns else pd.Series([False] * len(frame), index=frame.index)
    frame["_manual"] = manual
    rows = []
    for river, group in frame.groupby("river", dropna=False):
        risks = sorted(set(group.get("roi_risk", pd.Series(dtype=str)).dropna().astype(str)))
        rows.append(
            {
                "river": river,
                "roi_count": len(group),
                "manual_review_required_count": int(group["_manual"].sum()),
                "roi_risk_summary": ";".join(risks),
            }
        )
    return pd.DataFrame(rows)


def _by_river(labels: pd.DataFrame, matrix: pd.DataFrame, optical: pd.DataFrame, roi: pd.DataFrame) -> pd.DataFrame:
    roi_summary = _roi_summary(roi)
    rows = []
    for river in load_rivers():
        label_group = labels[labels["river"] == river] if not labels.empty else pd.DataFrame()
        usable = matrix[matrix["river"] == river] if not matrix.empty else pd.DataFrame()
        years = sorted(set(usable["year"].dropna().astype(int))) if not usable.empty and "year" in usable.columns else []
        row: dict[str, Any] = {
            "river": river,
            "total_doc_labels": len(label_group),
            "usable_doc_labels": len(usable),
            "year_min": min(years) if years else "",
            "year_max": max(years) if years else "",
            "n_years": len(years),
        }
        row.update(_predictor_stats(usable))
        _add_optical_counts(row, usable, optical)
        rows.append(row)
    out = pd.DataFrame(rows)
    if not roi_summary.empty:
        out = out.merge(roi_summary, on="river", how="left")
    for column in ["roi_count", "manual_review_required_count", "roi_risk_summary"]:
        if column not in out.columns:
            out[column] = 0 if column != "roi_risk_summary" else ""
    return out.fillna({"roi_count": 0, "manual_review_required_count": 0, "roi_risk_summary": ""})


def _by_year(labels: pd.DataFrame, matrix: pd.DataFrame, optical: pd.DataFrame) -> pd.DataFrame:
    years = sorted(set(pd.concat([labels.get("year", pd.Series(dtype=float)), matrix.get("year", pd.Series(dtype=float))], ignore_index=True).dropna().astype(int)))
    rows = []
    for year in years:
        label_group = labels[labels["year"].astype("Int64") == year] if not labels.empty else pd.DataFrame()
        usable = matrix[matrix["year"].astype("Int64") == year] if not matrix.empty else pd.DataFrame()
        row: dict[str, Any] = {
            "year": year,
            "total_doc_labels": len(label_group),
            "usable_doc_labels": len(usable),
            "n_rivers_with_usable_labels": int(usable["river"].nunique()) if not usable.empty else 0,
        }
        row.update(_predictor_stats(usable))
        _add_optical_counts(row, usable, optical)
        rows.append(row)
    return pd.DataFrame(rows)


def _snowmelt_window_candidates() -> list[Path]:
    names = [
        "snowmelt_windows.csv",
        "snowmelt_window_canonical.csv",
        "model_snowmelt_windows.csv",
    ]
    return [directory / name for directory in [PROCESSED_DIR, TABLE_DIR] for name in names]


def _load_snowmelt_windows() -> tuple[pd.DataFrame, str]:
    for candidate in _snowmelt_window_candidates():
        if not candidate.exists():
            continue
        try:
            frame = pd.read_csv(candidate)
        except Exception:
            continue
        lower = {str(column).lower(): column for column in frame.columns}
        if "river" not in lower:
            continue
        if {"start_date", "end_date"}.issubset(lower):
            out = frame.rename(columns={lower["river"]: "river", lower["start_date"]: "start_date", lower["end_date"]: "end_date"}).copy()
            out["start_date"] = _date_series(out["start_date"])
            out["end_date"] = _date_series(out["end_date"])
            out["window_source"] = str(candidate)
            return out, "snowmelt_window_table"
    return pd.DataFrame(), "may_july_provisional"


def _in_season_window(frame: pd.DataFrame, river: str, windows: pd.DataFrame, mode: str) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    if mode != "snowmelt_window_table" or windows.empty:
        return frame["date_dt"].dt.month.isin([5, 6, 7])
    mask = pd.Series([False] * len(frame), index=frame.index)
    river_windows = windows[windows["river"].astype(str) == river]
    for _, window in river_windows.iterrows():
        start = window.get("start_date")
        end = window.get("end_date")
        if pd.isna(start) or pd.isna(end):
            continue
        mask = mask | ((frame["date_dt"] >= start) & (frame["date_dt"] <= end))
    return mask


def _by_season_window(labels: pd.DataFrame, matrix: pd.DataFrame, optical: pd.DataFrame) -> pd.DataFrame:
    windows, mode = _load_snowmelt_windows()
    rows = []
    for river in load_rivers():
        label_group = labels[labels["river"] == river] if not labels.empty else pd.DataFrame()
        usable = matrix[matrix["river"] == river] if not matrix.empty else pd.DataFrame()
        label_window = label_group[_in_season_window(label_group, river, windows, mode)] if not label_group.empty else label_group
        usable_window = usable[_in_season_window(usable, river, windows, mode)] if not usable.empty else usable
        row: dict[str, Any] = {
            "river": river,
            "season_window": "snowmelt_window" if mode == "snowmelt_window_table" else "May-July provisional",
            "window_source": mode,
            "total_doc_labels_in_window": len(label_window),
            "usable_doc_labels_in_window": len(usable_window),
        }
        row.update(_predictor_stats(usable_window))
        _add_optical_counts(row, usable_window, optical)
        rows.append(row)
    return pd.DataFrame(rows)


def _source_composition(labels: pd.DataFrame, matrix: pd.DataFrame, discharge: pd.DataFrame, hydro: pd.DataFrame, optical: pd.DataFrame, roi: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tables = {
        "doc_labels_canonical": labels,
        "training_matrix_daily_predictable_labels": matrix,
        "daily_discharge_canonical": discharge,
        "daily_hydroclimate_canonical": hydro,
        "optical_timeseries_canonical": optical,
        "roi_catalog": roi,
    }
    for table_name, frame in tables.items():
        if frame.empty or "source_id" not in frame.columns:
            rows.append({"table": table_name, "source_id": "", "rows": 0})
            continue
        counts = frame.groupby("source_id", dropna=False).size().reset_index(name="rows")
        for _, row in counts.iterrows():
            rows.append({"table": table_name, "source_id": row["source_id"], "rows": int(row["rows"])})
    return pd.DataFrame(rows)


def _model_recommendations(by_river: pd.DataFrame, by_year: pd.DataFrame) -> pd.DataFrame:
    total_usable = int(by_river["usable_doc_labels"].sum()) if not by_river.empty else 0
    rivers_ge10 = int((by_river["usable_doc_labels"] >= 10).sum()) if not by_river.empty else 0
    years_ge5 = int((by_year["usable_doc_labels"] >= 5).sum()) if not by_year.empty else 0
    hydro_rows = int(by_river["labels_with_hydroclimate_predictors"].sum()) if not by_river.empty else 0
    q_rows = int(by_river["labels_with_Q_m3s"].sum()) if not by_river.empty else 0
    q_hydro_rows = int(by_river["labels_with_Q_and_hydroclimate_predictors"].sum()) if not by_river.empty else 0
    any_optical_3d = int(by_river["any_optical_match_3d"].sum()) if "any_optical_match_3d" in by_river.columns else 0
    hls_3d = int(by_river["hls_match_3d"].sum()) if "hls_match_3d" in by_river.columns else 0
    sentinel_3d = int(by_river["sentinel2_match_3d"].sum()) if "sentinel2_match_3d" in by_river.columns else 0

    rows = [
        {
            "model_scope": "DOC-only hydro-seasonal baseline",
            "minimum_sample_constraints": ">=50 usable DOC labels, >=3 rivers with >=10 labels, >=5 years with >=5 labels",
            "current_support": f"{total_usable} usable labels; {rivers_ge10} rivers >=10; {years_ge5} years >=5",
            "readiness": "ready" if total_usable >= 50 and rivers_ge10 >= 3 and years_ge5 >= 5 else "not_ready",
            "recommendation": "Can start as a baseline using DOC, river/group terms, and seasonal features only; do not treat this as final science.",
        },
        {
            "model_scope": "Hydroclimate model",
            "minimum_sample_constraints": ">=50 rows with Q_m3s and complete core hydroclimate predictors, >=3 rivers, grouped validation",
            "current_support": f"{q_hydro_rows} rows with both Q and complete hydroclimate predictors; Q={q_rows}; hydro={hydro_rows}",
            "readiness": "ready" if q_hydro_rows >= 50 and rivers_ge10 >= 3 else "needs_gap_filling",
            "recommendation": "Use only daily-predictable predictors from the training matrix; inspect predictor missingness before fitting.",
        },
        {
            "model_scope": "Optical sensitivity model",
            "minimum_sample_constraints": ">=30 DOC labels with any optical within +/-3 days and >=2 rivers; sensor-specific runs need enough rows per sensor",
            "current_support": f"any optical +/-3d={any_optical_3d}; HLS +/-3d={hls_3d}; Sentinel-2 +/-3d={sentinel_3d}",
            "readiness": "ready_for_sensitivity" if any_optical_3d >= 30 and (by_river["any_optical_match_3d"] >= 5).sum() >= 2 else "limited",
            "recommendation": "Use as sensitivity or matched-subset analysis only; satellite reflectance is an optical proxy, not a DOC observation.",
        },
    ]
    rows.append(
        {
            "model_scope": "Grouped validation",
            "minimum_sample_constraints": "leave-one-year-out: >=5 years with >=5 usable labels; leave-one-river-out: >=3 rivers with >=10 usable labels",
            "current_support": f"{years_ge5} eligible years; {rivers_ge10} eligible rivers",
            "readiness": "required_and_feasible" if years_ge5 >= 5 and rivers_ge10 >= 3 else "required_but_limited",
            "recommendation": "Use grouped validation because repeated dates, rivers, and legacy sources are not independent random samples.",
        }
    )
    return pd.DataFrame(rows)


def _overall_summary(by_river: pd.DataFrame) -> pd.DataFrame:
    if by_river.empty:
        return pd.DataFrame()
    totals = {
        "total_doc_labels": int(by_river["total_doc_labels"].sum()),
        "usable_doc_labels": int(by_river["usable_doc_labels"].sum()),
        "labels_with_Q_m3s": int(by_river["labels_with_Q_m3s"].sum()),
        "labels_with_hydroclimate_predictors": int(by_river["labels_with_hydroclimate_predictors"].sum()),
        "labels_with_Q_and_hydroclimate_predictors": int(by_river["labels_with_Q_and_hydroclimate_predictors"].sum()),
        "hls_match_0d": int(by_river["hls_match_0d"].sum()),
        "hls_match_1d": int(by_river["hls_match_1d"].sum()),
        "hls_match_3d": int(by_river["hls_match_3d"].sum()),
        "hls_match_7d": int(by_river["hls_match_7d"].sum()),
        "sentinel2_match_0d": int(by_river["sentinel2_match_0d"].sum()),
        "sentinel2_match_1d": int(by_river["sentinel2_match_1d"].sum()),
        "sentinel2_match_3d": int(by_river["sentinel2_match_3d"].sum()),
        "sentinel2_match_7d": int(by_river["sentinel2_match_7d"].sum()),
        "any_optical_match_0d": int(by_river["any_optical_match_0d"].sum()),
        "any_optical_match_1d": int(by_river["any_optical_match_1d"].sum()),
        "any_optical_match_3d": int(by_river["any_optical_match_3d"].sum()),
        "any_optical_match_7d": int(by_river["any_optical_match_7d"].sum()),
    }
    return pd.DataFrame([totals])


def generate_model_readiness_report() -> ReadinessOutputs:
    ensure_project_dirs()
    labels = _doc_labels(_read_processed("doc_labels_canonical"))
    matrix = _usable_matrix(_read_processed("training_matrix_daily_predictable"), labels)
    discharge = _read_processed("daily_discharge_canonical")
    hydro = _read_processed("daily_hydroclimate_canonical")
    optical = _read_processed("optical_timeseries_canonical")
    roi = _read_processed("roi_catalog")

    by_river = _by_river(labels, matrix, optical, roi)
    by_year = _by_year(labels, matrix, optical)
    by_season = _by_season_window(labels, matrix, optical)
    recommendations = _model_recommendations(by_river, by_year)
    source_composition = _source_composition(labels, matrix, discharge, hydro, optical, roi)
    overall = _overall_summary(by_river)
    roi_summary = _roi_summary(roi)
    source_priority_policy = _read_output_table("source_priority_policy.csv")
    training_source_audit = _read_output_table("training_matrix_source_audit.csv")
    basin_status = _read_output_table("basin_context_status.csv")
    gee_final_status = _read_output_table("gee_regeneration_final_status.csv")
    basin_value = str(basin_status.iloc[0].get("basin_context_status", "")) if not basin_status.empty else "unknown"
    if not basin_status.empty and "accepted_for_publication_grade_training" in basin_status.columns:
        basin_publication_ready = basin_status["accepted_for_publication_grade_training"].astype(str).str.lower().isin(["true", "1"]).any()
    else:
        basin_publication_ready = basin_value in {"complete", "upstream_basin_complete_with_hydroatlas", "upstream_basin_complete_attributes_partial"}
    publication_grade = basin_publication_ready and (
        not gee_final_status.empty
        and gee_final_status[gee_final_status["source_id"].astype(str) != "gee_smap_context_optional"]["accepted_for_publication_grade_training"].astype(str).str.lower().isin(["true", "1"]).all()
    )
    readiness_flags = pd.DataFrame(
        [
            {
                "READY_FOR_BASELINE_TRAINING": True,
                "READY_FOR_CORE_FULL_TRAINING": True,
                "READY_FOR_PUBLICATION_GRADE_TRAINING": bool(publication_grade),
                "basin_context_status": basin_value,
                "notes": "Core readiness assumes models do not require exact basin-level HydroBASINS/HydroATLAS attributes." if not publication_grade else "Publication-grade context available.",
            }
        ]
    )

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    by_river_path = TABLE_DIR / "model_readiness_by_river.csv"
    by_year_path = TABLE_DIR / "model_readiness_by_year.csv"
    by_season_path = TABLE_DIR / "model_readiness_by_season_window.csv"
    by_river.to_csv(by_river_path, index=False, encoding="utf-8")
    by_year.to_csv(by_year_path, index=False, encoding="utf-8")
    by_season.to_csv(by_season_path, index=False, encoding="utf-8")

    missing_cols = [column for column in by_river.columns if column.startswith("missing_") and column.endswith("_rate")]
    missing_rates = by_river[["river", *missing_cols]] if not by_river.empty else pd.DataFrame()

    lines = [
        "# Model Readiness Report",
        "",
        "This is a training-readiness audit only. No DOC model was trained.",
        "",
        "## Inputs",
        _md_table(pd.DataFrame({"input_table": READINESS_TABLES})),
        "",
        "## Overall Counts",
        _md_table(overall),
        "",
        "## Model Recommendations",
        _md_table(recommendations),
        "",
        "## Readiness Semantics",
        _md_table(readiness_flags),
        "",
        "## River Coverage",
        _md_table(by_river),
        "",
        "## Year Coverage",
        _md_table(by_year),
        "",
        "## Spring Freshet / Provisional Season Window",
        "If snowmelt-window tables are unavailable, this report uses a provisional May-July window.",
        "",
        _md_table(by_season),
        "",
        "## Missing Predictor Rates",
        _md_table(missing_rates),
        "",
        "## Source Composition",
        _md_table(source_composition),
        "",
        "## Source Priority Policy",
        _md_table(source_priority_policy),
        "",
        "## Training Matrix Source Priority Audit",
        _md_table(training_source_audit),
        "",
        "## ROI Risk and Manual Review",
        _md_table(roi_summary),
        "",
        "## Validation Guidance",
        "- Use grouped validation because river, year, and source-version effects are structured.",
        "- Prefer leave-one-year-out when enough labels exist per year.",
        "- Prefer leave-one-river-out for transferability checks across the six-river domain.",
        "- Keep optical sensitivity models separate from the daily-predictable hydroclimate model.",
        "",
        "## Explicit Boundaries",
        "- Do not train final DOC models from this command.",
        "- Do not use lab absorbance/CDOM as production daily predictors.",
        "- Do not treat satellite reflectance as direct DOC observations.",
        "- Do not silently merge TOC with DOC.",
    ]
    report_path = REPORT_DIR / "model_readiness_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return ReadinessOutputs(report_path, by_river_path, by_year_path, by_season_path)
