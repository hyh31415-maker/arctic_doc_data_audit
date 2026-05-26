from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from arctic_doc_data_audit.normalize import load_rivers
from arctic_doc_data_audit.paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, path


LEGACY_SOURCE = "old_arctic_doc_snowmelt_untrained_data"
REGENERATED_SOURCES = {
    "gee_hls_s30_l30",
    "gee_sentinel2_sr_harmonized",
    "gee_landsat_c2_l2",
    "gee_era5_land",
    "gee_modis_mod10a1",
}
FORBIDDEN_LAB_COLUMNS = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}


def _read(path_: Path) -> pd.DataFrame:
    assert path_.exists(), f"Missing expected file: {path_}"
    return pd.read_csv(path_)


def test_gee_auth_report_exists() -> None:
    report = REPORT_DIR / "gee_auth_check_report.md"
    table = TABLE_DIR / "gee_auth_check.csv"
    assert report.exists()
    frame = _read(table)
    assert {"ee_initialized", "can_access_test_collection", "credential_committed_to_git_check"}.issubset(frame.columns)
    text = report.read_text(encoding="utf-8").lower()
    assert "c:/users/hao/.config/earthengine/credentials" not in text
    assert "private_key" not in text
    assert "refresh_token" not in text


def test_regenerated_gee_rows_have_non_legacy_source_id() -> None:
    optical = _read(PROCESSED_DIR / "optical_timeseries_canonical.csv")
    hydro = _read(PROCESSED_DIR / "daily_hydroclimate_canonical.csv")
    regenerated = pd.concat(
        [
            optical[optical["quality_flag"].astype(str) == "regenerated_gee"][["source_id", "quality_flag"]],
            hydro[hydro["quality_flag"].astype(str) == "regenerated_gee"][["source_id", "quality_flag"]],
        ],
        ignore_index=True,
    )
    assert not regenerated.empty
    assert LEGACY_SOURCE not in set(regenerated["source_id"].astype(str))
    assert set(regenerated["source_id"].astype(str)).issubset(REGENERATED_SOURCES)


def test_training_matrix_prefers_regenerated_hydroclimate_over_legacy() -> None:
    matrix = _read(PROCESSED_DIR / "training_matrix_daily_predictable.csv")
    hydro = _read(PROCESSED_DIR / "daily_hydroclimate_canonical.csv")
    regen = hydro[
        (hydro["source_id"].astype(str) == "gee_era5_land")
        & hydro["temperature_2m_C"].notna()
    ][["river", "date", "temperature_2m_C"]].copy()
    merged = matrix.merge(regen, on=["river", "date"], suffixes=("_matrix", "_regenerated"))
    if merged.empty:
        pytest.skip("No label dates overlap regenerated ERA5-Land rows")
    sample = merged.iloc[0]
    assert abs(float(sample["temperature_2m_C_matrix"]) - float(sample["temperature_2m_C_regenerated"])) < 1e-9


def test_landsat_c2_rows_promote_to_optical_not_doc() -> None:
    optical = _read(PROCESSED_DIR / "optical_timeseries_canonical.csv")
    landsat = optical[optical["source_id"].astype(str) == "gee_landsat_c2_l2"]
    assert not landsat.empty
    assert set(landsat["sensor"].astype(str)) == {"Landsat"}
    labels = _read(PROCESSED_DIR / "doc_labels_canonical.csv")
    assert "gee_landsat_c2_l2" not in set(labels["source_id"].astype(str))


def test_sentinel2_all_six_river_plan_or_rows() -> None:
    rivers = set(load_rivers())
    optical = _read(PROCESSED_DIR / "optical_timeseries_canonical.csv")
    sentinel = optical[optical["source_id"].astype(str) == "gee_sentinel2_sr_harmonized"]
    if not sentinel.empty:
        assert set(sentinel["river"].dropna().astype(str)) == rivers
    else:
        plan = _read(TABLE_DIR / "gee_extraction_plan.csv")
        planned = plan[plan["source_id"].astype(str) == "gee_sentinel2_sr_harmonized"]
        assert set(planned["river"].dropna().astype(str)) == rivers


def test_basin_context_not_placeholder_if_full_ready_true() -> None:
    report = REPORT_DIR / "data_freeze_report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    if "READY_FOR_FULL_TRAINING: `True`" not in text:
        pytest.skip("Full freeze is not marked ready")
    status = _read(TABLE_DIR / "basin_context_status.csv")
    assert "placeholder_only" not in set(status["basin_context_status"].astype(str))
    assert status["accepted_for_full_training_readiness"].astype(str).str.lower().isin(["true", "1"]).any()


def test_datastream_deferred_not_blocking() -> None:
    status = _read(TABLE_DIR / "candidate_source_final_status.csv")
    row = status[status["source_id"].astype(str) == "datastream_mackenzie_candidate"]
    assert not row.empty
    assert row.iloc[0]["final_status"] == "deferred_by_user_not_blocking"
    assert str(row.iloc[0]["blocks_full_training"]).lower() in {"false", "0"}


def test_mdpi_manual_optional_not_blocking() -> None:
    status = _read(TABLE_DIR / "candidate_source_final_status.csv")
    row = status[status["source_id"].astype(str) == "partners_mdpi_eurasian_candidate"]
    assert not row.empty
    assert row.iloc[0]["final_status"] == "manual_required_optional_mechanism_source"
    assert str(row.iloc[0]["blocks_full_training"]).lower() in {"false", "0"}


def test_data_freeze_v2_hashes_exist() -> None:
    freeze_manifest = _read(TABLE_DIR / "data_freeze_manifest.csv")
    assert "data_freeze_20260526_v2" in set(freeze_manifest["freeze_id"].astype(str))
    hashes = _read(TABLE_DIR / "data_freeze_canonical_hashes.csv")
    assert not hashes.empty
    assert hashes["sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()


def test_no_model_prediction_flux_outputs_generated() -> None:
    model_dir = path("outputs", "models")
    if model_dir.exists():
        assert not any(item.is_file() for item in model_dir.rglob("*"))
    forbidden_ext = {".joblib", ".pkl"}
    generated = [
        item
        for item in path("outputs").rglob("*")
        if item.is_file() and item.suffix.lower() in forbidden_ext
    ]
    assert generated == []


def test_training_matrix_still_excludes_lab_absorbance_cdom() -> None:
    matrix = _read(PROCESSED_DIR / "training_matrix_daily_predictable.csv")
    assert not FORBIDDEN_LAB_COLUMNS.intersection(matrix.columns)
