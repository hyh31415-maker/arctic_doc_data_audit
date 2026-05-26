from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from arctic_doc_data_audit.normalize import load_rivers
from arctic_doc_data_audit.paths import path


GOLD_DIR = path("data", "processed", "gold")
GOLD_TABLE_DIR = path("outputs", "tables", "gold")
GOLD_REPORT_DIR = path("outputs", "reports", "gold")
RIVERS = set(load_rivers().keys())
LAB_FORBIDDEN = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}
ID_MEANS = {"HYBAS_ID_mean", "NEXT_DOWN_mean", "PFAF_ID_mean"}


def _read_csv(destination: Path) -> pd.DataFrame:
    assert destination.exists(), f"Missing expected file: {destination}"
    return pd.read_csv(destination, low_memory=False).fillna("")


def test_gold_tables_exist() -> None:
    required = {
        "doc_labels_gold.csv",
        "daily_discharge_gold.csv",
        "daily_hydroclimate_gold.csv",
        "optical_timeseries_gold.csv",
        "basin_context_gold.csv",
        "roi_catalog_gold.csv",
        "lab_optical_proxy_gold.csv",
    }
    assert required.issubset({item.name for item in GOLD_DIR.glob("*.csv")})


def test_gold_hashes_exist() -> None:
    hashes = _read_csv(GOLD_TABLE_DIR / "gold_table_hashes.csv")
    assert not hashes.empty
    assert hashes["sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    assert hashes["exists"].astype(str).str.lower().isin({"true", "1"}).all()


def test_doc_gold_no_toc() -> None:
    labels = _read_csv(GOLD_DIR / "doc_labels_gold.csv")
    assert not labels.empty
    assert set(labels["parameter_canonical"].astype(str)) == {"DOC"}
    assert not labels["is_toc_not_doc"].astype(str).str.lower().isin({"true", "1"}).any()


def test_hydrocore_expected_columns() -> None:
    matrix = _read_csv(GOLD_DIR / "training_matrix_hydrocore.csv")
    required = {
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
    }
    assert required.issubset(matrix.columns)
    assert not matrix.empty


def test_hydrocore_no_lab_optical_leakage() -> None:
    matrix = _read_csv(GOLD_DIR / "training_matrix_hydrocore.csv")
    assert LAB_FORBIDDEN.isdisjoint(matrix.columns)


def test_prediction_grid_has_no_doc() -> None:
    for name in ["prediction_grid_daily_hydrocore.csv", "prediction_grid_daily_with_basin_context.csv"]:
        grid = _read_csv(GOLD_DIR / name)
        assert "DOC_mgC_L" not in grid.columns


def test_prediction_grid_has_no_prediction_or_flux_columns() -> None:
    pattern = re.compile(r"prediction|pred_doc|flux|TgC|Mg_day", re.I)
    for name in ["prediction_grid_daily_hydrocore.csv", "prediction_grid_daily_with_basin_context.csv"]:
        grid = _read_csv(GOLD_DIR / name)
        assert [column for column in grid.columns if pattern.search(column)] == []


def test_optical_matched_3d_has_actual_bands() -> None:
    matrix = _read_csv(GOLD_DIR / "training_matrix_optical_matched_3d.csv")
    required = {"blue", "green", "red", "nir", "ndwi", "mndwi", "red_green_ratio", "green_blue_ratio"}
    assert required.issubset(matrix.columns)
    assert not matrix.empty
    assert matrix[["blue", "green", "red", "nir"]].replace("", pd.NA).notna().any().any()


def test_optical_match_deterministic_nearest_date() -> None:
    candidates = _read_csv(GOLD_DIR / "optical_match_candidates_3d.csv")
    selected = _read_csv(GOLD_DIR / "training_matrix_optical_matched_3d.csv")
    assert not candidates.empty
    assert not selected.empty
    candidates["abs_days_offset"] = pd.to_numeric(candidates["abs_days_offset"], errors="coerce")
    min_offset = candidates.groupby("label_id")["abs_days_offset"].min().to_dict()
    selected["abs_days_offset"] = pd.to_numeric(selected["days_offset"], errors="coerce").abs()
    checked = selected[selected["label_id"].isin(min_offset)]
    assert not checked.empty
    assert checked.apply(lambda row: row["abs_days_offset"] == min_offset[row["label_id"]], axis=1).all()


def test_optical_not_doc_label() -> None:
    labels = _read_csv(GOLD_DIR / "doc_labels_gold.csv")
    assert not labels["source_id"].astype(str).str.startswith("gee_").any()
    assert not labels["source_id"].astype(str).str.contains("hls|sentinel|landsat|optical", case=False, na=False).any()


def test_basin_curated_excludes_id_means() -> None:
    curated = _read_csv(GOLD_DIR / "basin_attributes_curated.csv")
    id_rows = curated[curated["source_field"].astype(str).isin(ID_MEANS)]
    if not id_rows.empty:
        assert not id_rows["model_use"].astype(str).str.lower().isin({"true", "1"}).any()
    wide = _read_csv(GOLD_DIR / "basin_attributes_curated_wide.csv")
    assert ID_MEANS.isdisjoint(wide.columns)


def test_basin_curated_six_rivers() -> None:
    curated = _read_csv(GOLD_DIR / "basin_attributes_curated.csv")
    assert set(curated["river"].astype(str)) == RIVERS


def test_basin_attributes_nonempty() -> None:
    basin = _read_csv(GOLD_DIR / "basin_context_gold.csv")
    assert set(basin["river"].astype(str)) == RIVERS
    assert basin["hydroatlas_attributes_json"].astype(str).ne("{}").all()
    curated = _read_csv(GOLD_DIR / "basin_attributes_curated.csv")
    usable = curated[curated["model_use"].astype(str).str.lower().isin({"true", "1"})]
    assert set(usable["river"].astype(str)) == RIVERS


def test_gold_qa_no_critical_issues() -> None:
    issues = _read_csv(GOLD_TABLE_DIR / "final_data_qa_issues.csv")
    if issues.empty:
        return
    assert not issues["severity"].astype(str).eq("critical").any()


def test_historical_failures_not_current_blockers() -> None:
    issues = _read_csv(GOLD_TABLE_DIR / "final_data_qa_issues.csv")
    if not issues.empty:
        blockers = issues[issues["blocking_for_gold_freeze"].astype(str).str.lower().isin({"true", "1"})]
        assert blockers.empty
        assert not issues["description"].astype(str).str.contains("B02 did not match|Dictionary.set|Number.divide", case=False, na=False).any()
    report_path = GOLD_REPORT_DIR / "data_freeze_gold_report.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
        assert "superseded" not in report.lower() or "GOLD_FREEZE_READY: `True`" in report


def test_no_model_prediction_flux_outputs_generated() -> None:
    forbidden_ext = {".joblib", ".pkl"}
    assert [item for item in path("outputs").rglob("*") if item.is_file() and item.suffix.lower() in forbidden_ext] == []
    model_dir = path("outputs", "models")
    if model_dir.exists():
        assert not any(model_dir.rglob("*"))
    forbidden_names = [
        item
        for item in path("outputs").rglob("*")
        if item.is_file() and ("doc_prediction" in item.name.lower() or item.name.lower().endswith("_flux.csv"))
    ]
    assert forbidden_names == []
