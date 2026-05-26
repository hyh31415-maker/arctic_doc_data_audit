from __future__ import annotations

import pandas as pd
import pytest

from arctic_doc_data_audit.manifest import read_manifest
from arctic_doc_data_audit.paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR
from arctic_doc_data_audit.preprocess.old_snapshot import (
    SOURCE_ID,
    build_old_snapshot_inventory,
    compare_old_raw_to_official,
)


def _inventory() -> pd.DataFrame:
    path = TABLE_DIR / "old_snapshot_inventory.csv"
    if path.exists():
        return pd.read_csv(path).fillna("")
    return build_old_snapshot_inventory()


def test_old_snapshot_inventory_counts() -> None:
    inventory = _inventory()
    manifest = read_manifest()
    manifest_count = int(((manifest["source_id"] == SOURCE_ID) & (manifest["download_status"] == "downloaded")).sum())
    assert len(inventory) == manifest_count
    assert {"data/raw", "data/raw_external", "data/interim"}.issubset(set(inventory["old_project_subdir"]))


def test_no_model_prediction_flux_promoted() -> None:
    inventory = _inventory()
    token_mask = inventory["file_name"].str.contains("model|prediction|flux|joblib|pkl", case=False, regex=True, na=False)
    if token_mask.any():
        assert not inventory.loc[token_mask, "promotable_to_canonical"].astype(bool).any()
    canonical_targets = set(inventory.loc[token_mask, "target_canonical_table"].dropna().astype(str))
    assert not canonical_targets.intersection({"doc_labels_canonical", "daily_hydroclimate_canonical", "optical_timeseries_canonical"})


def test_old_hls_promotes_to_optical_not_doc() -> None:
    inventory = _inventory()
    hls = inventory[inventory["file_name"].isin(["hls_reflectance_timeseries.csv", "hls_features.csv"])]
    assert not hls.empty
    assert set(hls["target_canonical_table"]) == {"optical_timeseries_canonical"}
    doc_path = PROCESSED_DIR / "doc_labels_canonical.csv"
    if doc_path.exists():
        doc = pd.read_csv(doc_path)
        assert SOURCE_ID not in set(doc.get("source_id", pd.Series(dtype=str)).astype(str))


def test_old_sentinel2_promotes_to_optical_not_doc() -> None:
    inventory = _inventory()
    sentinel = inventory[inventory["file_name"].eq("sentinel2_reflectance_final_primary.csv")]
    assert not sentinel.empty
    assert set(sentinel["target_canonical_table"]) == {"optical_timeseries_canonical"}
    optical_path = PROCESSED_DIR / "optical_timeseries_canonical.csv"
    if not optical_path.exists():
        pytest.skip("optical_timeseries_canonical.csv has not been generated yet")
    optical = pd.read_csv(optical_path)
    promoted = optical[
        (optical.get("source_id", pd.Series(dtype=str)).astype(str) == SOURCE_ID)
        & (optical.get("sensor", pd.Series(dtype=str)).astype(str) == "Sentinel-2")
    ]
    assert not promoted.empty
    assert set(promoted["roi_set"].dropna().astype(str)) == {"final_primary"}
    doc_path = PROCESSED_DIR / "doc_labels_canonical.csv"
    if doc_path.exists():
        doc = pd.read_csv(doc_path)
        assert SOURCE_ID not in set(doc.get("source_id", pd.Series(dtype=str)).astype(str))


def test_old_era5_modis_promotes_to_hydroclimate() -> None:
    inventory = _inventory()
    hydro = inventory[inventory["file_name"].isin(["era5_land_daily.csv", "modis_snow_daily.csv"])]
    assert not hydro.empty
    assert set(hydro["target_canonical_table"]) == {"daily_hydroclimate_canonical"}
    hydro_path = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    if not hydro_path.exists():
        pytest.skip("daily_hydroclimate_canonical.csv has not been generated yet")
    canonical = pd.read_csv(hydro_path)
    assert (canonical.get("source_id", pd.Series(dtype=str)).astype(str) == SOURCE_ID).any()


def test_temp2m_mean_k_converts_to_celsius() -> None:
    source_path = (
        PROCESSED_DIR.parent
        / "raw_external"
        / "old_project_snapshot"
        / "data"
        / "interim"
        / "longterm_hydroclimate"
        / "by_river"
        / "lena"
        / "era5_land_daily_2000_2024.csv"
    )
    if not source_path.exists():
        pytest.skip("old snapshot ERA5 source file is not available")
    hydro_path = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    if not hydro_path.exists():
        pytest.skip("daily_hydroclimate_canonical.csv has not been generated yet")
    source = pd.read_csv(source_path)
    sample = source[source["temp2m_mean_K"].notna()].iloc[0]
    canonical = pd.read_csv(hydro_path)
    row = canonical[(canonical["river"] == "Lena") & (canonical["date"].astype(str) == str(sample["date"]))]
    assert not row.empty
    assert abs(float(row.iloc[0]["temperature_2m_C"]) - (float(sample["temp2m_mean_K"]) - 273.15)) < 1e-6


def test_snowmelt_total_m_maps_to_snowmelt_m() -> None:
    source_path = (
        PROCESSED_DIR.parent
        / "raw_external"
        / "old_project_snapshot"
        / "data"
        / "interim"
        / "longterm_hydroclimate"
        / "by_river"
        / "lena"
        / "era5_land_daily_2000_2024.csv"
    )
    if not source_path.exists():
        pytest.skip("old snapshot ERA5 source file is not available")
    hydro_path = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    if not hydro_path.exists():
        pytest.skip("daily_hydroclimate_canonical.csv has not been generated yet")
    source = pd.read_csv(source_path)
    sample = source[source["snowmelt_total_m"].notna()].iloc[0]
    canonical = pd.read_csv(hydro_path)
    row = canonical[(canonical["river"] == "Lena") & (canonical["date"].astype(str) == str(sample["date"]))]
    assert not row.empty
    assert abs(float(row.iloc[0]["snowmelt_m"]) - float(sample["snowmelt_total_m"])) < 1e-12


def test_training_matrix_no_lab_optical_leakage() -> None:
    matrix_path = PROCESSED_DIR / "training_matrix_daily_predictable.csv"
    if not matrix_path.exists():
        pytest.skip("training matrix has not been generated yet")
    matrix = pd.read_csv(matrix_path)
    forbidden = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}
    assert not forbidden.intersection(matrix.columns)


def test_report_exclusion_reason_does_not_include_nan() -> None:
    report_path = REPORT_DIR / "data_availability_report.md"
    if not report_path.exists():
        pytest.skip("data availability report has not been generated yet")
    text = report_path.read_text(encoding="utf-8")
    section = text.split("## 11. Unavailable Records and Exclusion Reasons", 1)[-1].split("## 12.", 1)[0]
    assert "| nan " not in section.lower()
    assert " nan |" not in section.lower()


def test_old_raw_duplicate_official_preference() -> None:
    inventory = _inventory()
    compare, _ = compare_old_raw_to_official(inventory)
    same_hash = compare[compare["same_hash"].astype(bool)]
    assert not same_hash.empty
    assert set(same_hash["decision"]) == {"duplicate_of_official_current"}
