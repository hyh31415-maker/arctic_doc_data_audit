from __future__ import annotations

import math

import pandas as pd

from ..paths import PROCESSED_DIR
from ..schemas import ensure_columns, read_table_if_exists, write_table


FORBIDDEN = {"A254", "A350", "A355", "A375", "A412", "A420", "A440", "SUVA254", "spectral_slope_275_295", "spectral_slope_350_400"}


def run() -> pd.DataFrame:
    labels = read_table_if_exists("doc_labels_canonical")
    discharge = read_table_if_exists("daily_discharge_canonical")
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    optical = read_table_if_exists("optical_timeseries_canonical")
    basin = read_table_if_exists("basin_context_canonical")

    if labels.empty:
        frame = ensure_columns(pd.DataFrame(), "training_matrix_daily_predictable")
        write_table(frame, "training_matrix_daily_predictable", PROCESSED_DIR / "training_matrix_daily_predictable.csv")
        return frame

    usable = labels[
        (labels["parameter_canonical"] == "DOC")
        & (labels["can_train_doc_model"].astype(str).str.lower().isin(["true", "1"]))
        & (labels["preferred_record"].astype(str).str.lower().isin(["true", "1"]))
    ].copy()
    usable["date"] = pd.to_datetime(usable["date"], errors="coerce").dt.date.astype(str)
    out = usable[["label_id", "river", "date", "value_mgC_L", "doy", "provenance_tier", "usability_tier"]].rename(columns={"value_mgC_L": "DOC_mgC_L"})

    if not discharge.empty:
        discharge = discharge.copy()
        discharge["date"] = pd.to_datetime(discharge["date"], errors="coerce").dt.date.astype(str)
        discharge = discharge.sort_values(["river", "date"]).drop_duplicates(["river", "date"], keep="last")
        out = out.merge(discharge[["river", "date", "Q_m3s"]], on=["river", "date"], how="left")
    else:
        out["Q_m3s"] = pd.NA

    if not hydro.empty:
        hydro = hydro.copy()
        hydro["date"] = pd.to_datetime(hydro["date"], errors="coerce").dt.date.astype(str)
        hydro_cols = ["river", "date", "temperature_2m_C", "positive_degree_day_Cday", "snow_cover_fraction", "snow_depletion_rate_7d", "surface_runoff_m"]
        out = out.merge(hydro[hydro_cols], on=["river", "date"], how="left")
    for column in ["temperature_2m_C", "positive_degree_day_Cday", "snow_cover_fraction", "snow_depletion_rate_7d", "surface_runoff_m"]:
        if column not in out.columns:
            out[column] = pd.NA

    out["doy"] = pd.to_numeric(out["doy"], errors="coerce")
    out["sin_doy"] = out["doy"].map(lambda value: math.sin(2 * math.pi * value / 366) if pd.notna(value) else pd.NA)
    out["cos_doy"] = out["doy"].map(lambda value: math.cos(2 * math.pi * value / 366) if pd.notna(value) else pd.NA)
    out["flushing_potential_index"] = pd.NA
    out["dilution_potential_index"] = pd.NA

    basin_rivers = set(basin["river"].dropna().astype(str)) if not basin.empty else set()
    out["basin_context_available"] = out["river"].astype(str).isin(basin_rivers)

    for sensor, column in [("HLS", "optical_match_hls_available"), ("Sentinel-2", "optical_match_sentinel2_available"), ("Landsat", "optical_match_landsat_available")]:
        if optical.empty:
            out[column] = False
            continue
        matches = optical[optical["sensor"].astype(str).str.contains(sensor, case=False, na=False)][["river", "date"]].drop_duplicates()
        matches["date"] = pd.to_datetime(matches["date"], errors="coerce").dt.date.astype(str)
        key = set(zip(matches["river"].astype(str), matches["date"].astype(str)))
        out[column] = list(zip(out["river"].astype(str), out["date"].astype(str)))
        out[column] = out[column].map(lambda value: value in key)

    frame = ensure_columns(out, "training_matrix_daily_predictable")
    leak = FORBIDDEN.intersection(frame.columns)
    if leak:
        raise ValueError(f"Lab optical leakage in training matrix: {sorted(leak)}")
    write_table(frame, "training_matrix_daily_predictable", PROCESSED_DIR / "training_matrix_daily_predictable.csv")
    return frame

