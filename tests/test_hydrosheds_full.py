from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from arctic_doc_data_audit.normalize import load_rivers
from arctic_doc_data_audit.paths import PROCESSED_DIR, REPORT_DIR, TABLE_DIR, path


RIVERS = set(load_rivers().keys())


def _read(destination: Path) -> pd.DataFrame:
    assert destination.exists(), f"Missing expected file: {destination}"
    return pd.read_csv(destination).fillna("")


def _freeze_text() -> str:
    report = REPORT_DIR / "data_freeze_report.md"
    assert report.exists()
    return report.read_text(encoding="utf-8")


def _publication_ready() -> bool:
    return "READY_FOR_PUBLICATION_GRADE_TRAINING: `True`" in _freeze_text()


def test_full_hydrosheds_download_inventory_exists() -> None:
    inventory = _read(TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    assert {"source_id", "download_url", "download_status", "sha256", "license_or_citation"}.issubset(inventory.columns)
    assert {"hydrobasins_standard_full", "hydrorivers_global", "basinatlas_global_gdb", "riveratlas_global_gdb"}.issubset(set(inventory["source_id"].astype(str)))


def test_hydroatlas_uses_stable_ndownloader_urls() -> None:
    inventory = _read(TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    hydroatlas = inventory[inventory["source_id"].astype(str).str.contains("atlas", case=False, na=False)]
    assert not hydroatlas.empty
    urls = " ".join(hydroatlas["download_url"].astype(str))
    assert "figshare.com/ndownloader" not in urls
    required = hydroatlas[hydroatlas["source_id"].astype(str).isin(["basinatlas_global_gdb", "riveratlas_global_gdb", "lakeatlas_global_gdb"])]
    assert required["download_url"].astype(str).str.startswith("https://ndownloader.figshare.com/files/").all()
    assert required["size_check_status"].astype(str).eq("ok").all()


def test_hydrobasins_all_or_selected_levels_are_indexed_when_downloaded() -> None:
    inventory = _read(TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    downloaded = inventory[
        (inventory["source_id"].astype(str) == "hydrobasins_standard_full")
        & inventory["download_status"].astype(str).isin(["downloaded", "already_present"])
    ]
    index = _read(TABLE_DIR / "hydrobasins_layer_index.csv")
    if downloaded.empty:
        assert not _publication_ready()
        return
    ok = index[index["read_status"].astype(str).eq("ok")]
    assert not ok.empty
    assert {"06", "07", "08", "09"}.intersection(set(ok["level"].astype(str).str.zfill(2)))


def test_hydrorivers_global_file_is_indexed_when_downloaded() -> None:
    inventory = _read(TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    downloaded = inventory[
        (inventory["source_id"].astype(str) == "hydrorivers_global")
        & inventory["download_status"].astype(str).isin(["downloaded", "already_present"])
    ]
    index = _read(TABLE_DIR / "hydrorivers_layer_index.csv")
    if downloaded.empty:
        assert not _publication_ready()
        return
    assert (index["read_status"].astype(str) == "ok").any()
    assert (index["region"].astype(str).eq("Global") | index["dataset_family"].astype(str).str.contains("hydrorivers", case=False)).any()


def test_basinatlas_and_riveratlas_are_indexed_when_downloaded() -> None:
    inventory = _read(TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    index = _read(TABLE_DIR / "hydroatlas_layer_index.csv")
    for source_id, family in [("basinatlas_global_gdb", "basinatlas"), ("riveratlas_global_gdb", "riveratlas")]:
        downloaded = inventory[(inventory["source_id"].astype(str) == source_id) & inventory["download_status"].astype(str).isin(["downloaded", "already_present"])]
        if downloaded.empty:
            assert not _publication_ready()
            continue
        subset = index[(index["dataset_family"].astype(str) == family) & (index["read_status"].astype(str) == "ok")]
        assert not subset.empty


def test_station_to_hydrorivers_match_exists_for_all_six_when_available() -> None:
    matches = _read(TABLE_DIR / "station_to_hydroriver_match.csv")
    assert set(matches["river"].astype(str)) == RIVERS
    if (matches["match_status"].astype(str) == "matched").all():
        assert matches["matched_hyriv_id"].astype(str).ne("").all()
    else:
        assert not _publication_ready()


def test_station_to_hydrobasins_match_exists_for_all_six_when_available() -> None:
    matches = _read(TABLE_DIR / "station_to_hydrobasin_match.csv")
    assert set(matches["river"].astype(str)) == RIVERS
    primary = matches[matches["selected_primary"].astype(str).str.lower().isin(["true", "1"])]
    if len(primary) == 6 and (primary["match_status"].astype(str) == "matched").all():
        assert set(primary["river"].astype(str)) == RIVERS
        assert primary["matched_hybas_id"].astype(str).ne("").all()
    else:
        assert not _publication_ready()


def test_upstream_aggregation_exists_for_all_six_when_matches_available() -> None:
    agg = _read(TABLE_DIR / "upstream_basin_aggregation.csv")
    assert set(agg["river"].astype(str)) == RIVERS
    complete = agg[agg["aggregation_status"].astype(str).eq("complete")]
    if len(complete) == 6:
        assert set(complete["river"].astype(str)) == RIVERS
        assert pd.to_numeric(complete["upstream_area_km2"], errors="coerce").notna().all()
    else:
        assert not _publication_ready()


def test_upstream_area_is_much_larger_than_roi_area_when_complete() -> None:
    agg = _read(TABLE_DIR / "upstream_basin_aggregation.csv")
    roi = _read(PROCESSED_DIR / "roi_catalog.csv")
    complete = agg[agg["aggregation_status"].astype(str).eq("complete")].copy()
    if complete.empty:
        assert not _publication_ready()
        return
    roi_primary = roi[roi["roi_set"].astype(str).eq("final_primary")][["river", "roi_area_m2"]].copy()
    roi_primary["roi_area_km2"] = pd.to_numeric(roi_primary["roi_area_m2"], errors="coerce") / 1_000_000
    merged = complete.merge(roi_primary[["river", "roi_area_km2"]], on="river", how="left")
    merged["upstream_area_km2"] = pd.to_numeric(merged["upstream_area_km2"], errors="coerce")
    comparable = merged[merged["roi_area_km2"].notna() & (merged["roi_area_km2"] > 0)]
    if not comparable.empty:
        assert (comparable["upstream_area_km2"] > comparable["roi_area_km2"] * 10).all()


def test_basin_context_no_roi_approximate_if_hydrobasins_success() -> None:
    basin = _read(PROCESSED_DIR / "basin_context_canonical.csv")
    status = _read(TABLE_DIR / "basin_context_status.csv")
    publication_status = status["accepted_for_publication_grade_training"].astype(str).str.lower().isin(["true", "1"]).any()
    if publication_status:
        assert not basin["geometry_source"].astype(str).str.contains("roi", case=False, na=False).any()
        assert basin["quality_flag"].astype(str).isin(["upstream_basin_complete_with_hydroatlas", "upstream_basin_complete_attributes_partial"]).all()
    else:
        assert not _publication_ready()


def test_hydroatlas_attributes_json_not_empty_if_extraction_succeeds() -> None:
    attrs = _read(TABLE_DIR / "hydroatlas_attributes_by_river.csv")
    successful = attrs[attrs["extraction_status"].astype(str).eq("attributes_extracted_not_fully_aggregated")]
    if successful.empty:
        assert not _publication_ready()
        return
    for value in successful["hydroatlas_attributes_json"].astype(str):
        assert value and value != "{}"
        assert json.loads(value)


def test_publication_grade_ready_only_with_all_six_upstream_context() -> None:
    agg = _read(TABLE_DIR / "upstream_basin_aggregation.csv")
    status = _read(TABLE_DIR / "basin_context_status.csv")
    all_six_complete = set(agg[agg["aggregation_status"].astype(str).eq("complete")]["river"].astype(str)) == RIVERS
    publication_status = status["accepted_for_publication_grade_training"].astype(str).str.lower().isin(["true", "1"]).any()
    if publication_status or _publication_ready():
        assert all_six_complete
        assert set(_read(PROCESSED_DIR / "basin_context_canonical.csv")["river"].astype(str)) == RIVERS
    else:
        assert "READY_FOR_PUBLICATION_GRADE_TRAINING: `False`" in _freeze_text()


def test_no_model_prediction_flux_outputs_generated_by_hydrosheds_workflow() -> None:
    forbidden_ext = {".joblib", ".pkl"}
    assert [item for item in path("outputs").rglob("*") if item.is_file() and item.suffix.lower() in forbidden_ext] == []
    model_dir = path("outputs", "models")
    if model_dir.exists():
        assert not any(model_dir.rglob("*"))
    output_names = [item.name.lower() for item in path("outputs").rglob("*") if item.is_file()]
    assert not any("doc_prediction" in name or name.endswith("_flux.csv") for name in output_names)
