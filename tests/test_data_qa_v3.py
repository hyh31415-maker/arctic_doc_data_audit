from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.gee_regeneration import resolve_band, resolve_band_map, safe_pct_valid
from arctic_doc_data_audit.paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, path


def _table(name: str) -> pd.DataFrame:
    destination = TABLE_DIR / name
    assert destination.exists(), f"Missing expected table: {destination}"
    return pd.read_csv(destination).fillna("")


def test_hls_band_resolver_maps_b2_without_b02() -> None:
    available = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "Fmask"]
    assert resolve_band(available, "blue", ["B2", "B02", "blue"]) == "B2"
    resolved, missing = resolve_band_map(
        available,
        {
            "blue": ["B2", "B02"],
            "green": ["B3", "B03"],
            "red": ["B4", "B04"],
        },
    )
    assert resolved == {"B2": "blue", "B3": "green", "B4": "red"}
    assert missing == []


def test_no_current_hls_failure_reason_contains_b02_mismatch() -> None:
    summary = _table("gee_hls_extraction_summary.csv")
    reasons = " ".join(summary.get("failure_reason", pd.Series(dtype=str)).astype(str))
    assert "B02' did not match" not in reasons
    assert "B02 did not match" not in reasons


def test_modis_null_total_pixels_do_not_divide() -> None:
    assert safe_pct_valid(10, None) is None
    assert safe_pct_valid(10, 0) is None
    assert safe_pct_valid(None, 20) is None
    assert safe_pct_valid(10, 20) == 0.5


def test_gee_null_value_qc_exists_without_dictionary_set_failure() -> None:
    qc = _table("gee_null_value_qc.csv")
    assert {"source_id", "river", "year", "date", "variable", "null_reason"}.issubset(qc.columns)
    text = " ".join(qc.astype(str).agg(" ".join, axis=1).head(500).tolist())
    assert "Dictionary.set() missing" not in text


def test_training_matrix_prefers_regenerated_hydroclimate_over_legacy_v3() -> None:
    audit = _table("training_matrix_source_audit.csv")
    assert not audit.empty
    assert (audit["hydroclimate_source_id_used"].astype(str).str.startswith("gee_")).any()
    hydro = pd.read_csv(PROCESSED_DIR / "daily_hydroclimate_canonical.csv")
    regenerated_temp_keys = set(
        zip(
            hydro[(hydro["source_id"].astype(str) == "gee_era5_land") & hydro["temperature_2m_C"].notna()]["river"].astype(str),
            hydro[(hydro["source_id"].astype(str) == "gee_era5_land") & hydro["temperature_2m_C"].notna()]["date"].astype(str),
        )
    )
    check = audit[audit.apply(lambda row: (str(row["river"]), str(row["date"])) in regenerated_temp_keys, axis=1)]
    assert not check.empty
    assert set(check["temperature_2m_source_id_used"].astype(str)) == {"gee_era5_land"}


def test_optical_matching_distinguishes_regenerated_vs_legacy() -> None:
    audit = _table("training_matrix_source_audit.csv")
    required = {
        "has_regenerated_hls_match_3d",
        "has_legacy_hls_match_3d",
        "has_regenerated_sentinel2_match_3d",
        "has_legacy_sentinel2_match_3d",
        "has_landsat_match_3d",
    }
    assert required.issubset(audit.columns)
    assert audit["optical_match_source_priority"].isin(["regenerated", "legacy", "no_optical"]).all()


def test_approximate_basin_context_not_publication_ready() -> None:
    report = (REPORT_DIR / "data_freeze_report.md").read_text(encoding="utf-8")
    if "basin_context_status: `approximate_roi_context`" in report:
        assert "READY_FOR_PUBLICATION_GRADE_TRAINING: `False`" in report
    elif "READY_FOR_PUBLICATION_GRADE_TRAINING: `True`" in report:
        status = _table("basin_context_status.csv")
        assert status["accepted_for_publication_grade_training"].astype(str).str.lower().isin(["true", "1"]).any()
    else:
        assert "READY_FOR_PUBLICATION_GRADE_TRAINING: `False`" in report


def test_datastream_and_mdpi_do_not_block_core_full_readiness() -> None:
    status = _table("candidate_source_final_status.csv")
    datastream = status[status["source_id"].eq("datastream_mackenzie_candidate")].iloc[0]
    mdpi = status[status["source_id"].eq("partners_mdpi_eurasian_candidate")].iloc[0]
    assert datastream["final_status"] == "deferred_by_user_not_blocking"
    assert mdpi["final_status"] == "manual_required_optional_mechanism_source"
    assert str(datastream["blocks_full_training"]).lower() in {"false", "0"}
    assert str(mdpi["blocks_full_training"]).lower() in {"false", "0"}
    issues = _table("data_qa_issues.csv")
    core_blockers = issues[issues["blocking_for_full_training"].astype(str).str.lower().isin(["true", "1"])]
    assert "datastream_mackenzie_candidate" not in set(core_blockers["source_id"].astype(str))
    assert "partners_mdpi_eurasian_candidate" not in set(core_blockers["source_id"].astype(str))


def test_wqp_candidate_labels_not_promoted_by_default_v3() -> None:
    plan = _table("candidate_label_promotion_plan.csv")
    if not plan.empty:
        assert not plan["approved_for_promotion"].astype(str).str.lower().isin(["true", "1"]).any()
    labels = pd.read_csv(PROCESSED_DIR / "doc_labels_canonical.csv")
    assert "wqp_usgs_yukon_candidate" not in set(labels["source_id"].astype(str))


def test_landsat_rows_are_optical_only_never_doc() -> None:
    optical = pd.read_csv(PROCESSED_DIR / "optical_timeseries_canonical.csv")
    assert (optical["source_id"].astype(str) == "gee_landsat_c2_l2").any()
    labels = pd.read_csv(PROCESSED_DIR / "doc_labels_canonical.csv")
    assert "gee_landsat_c2_l2" not in set(labels["source_id"].astype(str))


def test_no_model_prediction_flux_outputs_from_data_qa() -> None:
    forbidden_ext = {".joblib", ".pkl"}
    assert [item for item in path("outputs").rglob("*") if item.is_file() and item.suffix.lower() in forbidden_ext] == []
    model_dir = path("outputs", "models")
    if model_dir.exists():
        assert not any(model_dir.rglob("*"))
