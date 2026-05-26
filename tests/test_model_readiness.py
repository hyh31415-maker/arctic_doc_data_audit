from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.model_readiness import generate_model_readiness_report
from arctic_doc_data_audit.paths import REPORT_DIR, TABLE_DIR


def test_model_readiness_outputs_are_generated() -> None:
    outputs = generate_model_readiness_report()
    assert outputs.report_path.exists()
    assert outputs.by_river_path.exists()
    assert outputs.by_year_path.exists()
    assert outputs.by_season_window_path.exists()

    report = (REPORT_DIR / "model_readiness_report.md").read_text(encoding="utf-8")
    assert "No DOC model was trained" in report
    assert "Model Recommendations" in report


def test_model_readiness_by_river_required_columns() -> None:
    generate_model_readiness_report()
    by_river = pd.read_csv(TABLE_DIR / "model_readiness_by_river.csv")
    required = {
        "river",
        "total_doc_labels",
        "usable_doc_labels",
        "labels_with_Q_m3s",
        "labels_with_hydroclimate_predictors",
        "hls_match_0d",
        "hls_match_1d",
        "hls_match_3d",
        "hls_match_7d",
        "sentinel2_match_0d",
        "sentinel2_match_1d",
        "sentinel2_match_3d",
        "sentinel2_match_7d",
        "any_optical_match_0d",
        "any_optical_match_1d",
        "any_optical_match_3d",
        "any_optical_match_7d",
        "manual_review_required_count",
    }
    assert required.issubset(by_river.columns)


def test_model_readiness_season_window_uses_provisional_or_snowmelt_source() -> None:
    generate_model_readiness_report()
    by_season = pd.read_csv(TABLE_DIR / "model_readiness_by_season_window.csv")
    assert {"river", "season_window", "window_source", "usable_doc_labels_in_window"}.issubset(by_season.columns)
    assert set(by_season["window_source"].dropna().astype(str)).issubset({"may_july_provisional", "snowmelt_window_table"})


def test_model_readiness_no_lab_absorbance_columns() -> None:
    generate_model_readiness_report()
    forbidden = {"A254", "A375", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}
    for name in [
        "model_readiness_by_river.csv",
        "model_readiness_by_year.csv",
        "model_readiness_by_season_window.csv",
    ]:
        frame = pd.read_csv(TABLE_DIR / name)
        assert not forbidden.intersection(frame.columns)
