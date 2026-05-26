from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.data_completion import WQP_QC_COLUMNS, classify_candidate_parameter, freeze_data
from arctic_doc_data_audit.paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR


def _table(name: str) -> pd.DataFrame:
    path = TABLE_DIR / name
    assert path.exists(), f"Missing expected table: {path}"
    return pd.read_csv(path)


def _ensure_freeze_outputs() -> None:
    if not (TABLE_DIR / "data_freeze_canonical_hashes.csv").exists() or not (REPORT_DIR / "data_freeze_report.md").exists():
        freeze_data("data_freeze_test_v1", run_tests=False)


def test_wqp_candidate_table_schema() -> None:
    frame = _table("wqp_usgs_candidate_label_qc.csv")
    assert set(WQP_QC_COLUMNS).issubset(frame.columns)


def test_datastream_candidate_table_schema() -> None:
    frame = _table("datastream_mackenzie_candidate_label_qc.csv")
    assert set(WQP_QC_COLUMNS).issubset(frame.columns)


def test_toc_remains_toc() -> None:
    parameter, is_toc, reason = classify_candidate_parameter("Total organic carbon", "Total", "mg/L")
    assert parameter == "TOC"
    assert is_toc is True
    assert reason == ""


def test_candidate_labels_not_promoted_by_default() -> None:
    plan = _table("candidate_label_promotion_plan.csv")
    if not plan.empty:
        assert not plan["approved_for_promotion"].astype(str).str.lower().isin(["true", "1"]).any()
    labels = pd.read_csv(PROCESSED_DIR / "doc_labels_canonical.csv")
    external_sources = {"wqp_usgs_yukon_candidate", "datastream_mackenzie_candidate", "partners_mdpi_eurasian_candidate"}
    assert not external_sources.intersection(set(labels["source_id"].astype(str)))


def test_candidate_duplicate_decisions_prefer_arcticgro_current() -> None:
    decisions = _table("candidate_label_duplicate_decisions.csv")
    assert "arcticgro_current_preferred" in set(decisions["decision"].astype(str))


def test_freeze_manifest_includes_hashes_for_canonical_tables() -> None:
    _ensure_freeze_outputs()
    hashes = _table("data_freeze_canonical_hashes.csv")
    assert {"table_name", "sha256", "row_count"}.issubset(hashes.columns)
    assert "doc_labels_canonical" in set(hashes["table_name"].astype(str))
    assert hashes["sha256"].astype(str).str.len().ge(64).any()


def test_freeze_report_says_no_model_trained() -> None:
    _ensure_freeze_outputs()
    report = (REPORT_DIR / "data_freeze_report.md").read_text(encoding="utf-8")
    assert "No DOC model was trained" in report


def test_gee_extraction_plan_exists_even_without_ee() -> None:
    plan = _table("gee_extraction_plan.csv")
    assert not plan.empty
    assert {"source_id", "collection", "river", "needs_regeneration", "command", "blocking_reason"}.issubset(plan.columns)


def test_basin_context_placeholder_is_not_complete() -> None:
    status = _table("hydrobasins_hydroatlas_acquisition_status.csv")
    assert "complete" not in set(status["overall_basin_context_status"].astype(str))


def test_training_matrix_still_excludes_lab_absorbance_cdom() -> None:
    matrix = pd.read_csv(PROCESSED_DIR / "training_matrix_daily_predictable.csv")
    forbidden = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}
    assert not forbidden.intersection(matrix.columns)
