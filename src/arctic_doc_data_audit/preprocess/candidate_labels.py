from __future__ import annotations

import math

import pandas as pd

from ..normalize import clean_text, coordinates_for_river
from ..paths import RAW_EXTERNAL_DIR, TABLE_DIR


QC_COLUMNS = [
    "source_id",
    "site_id",
    "site_name",
    "river_target",
    "characteristic",
    "result_value",
    "unit",
    "method",
    "filtered_or_unfiltered",
    "medium",
    "site_type",
    "latitude",
    "longitude",
    "station_distance_to_target_km",
    "usability_tier",
    "notes",
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _wqp_column(frame: pd.DataFrame, *names: str) -> str | None:
    lookup = {clean_text(column).lower(): column for column in frame.columns}
    for name in names:
        found = lookup.get(name.lower())
        if found:
            return found
    return None


def build_wqp_candidate_qc() -> pd.DataFrame:
    files = sorted((RAW_EXTERNAL_DIR / "wqp_usgs").glob("*.csv"))
    rows = []
    target_lat, target_lon = coordinates_for_river("Yukon")
    for file in files:
        frame = pd.read_csv(file, dtype=str)
        site_id_col = _wqp_column(frame, "MonitoringLocationIdentifier")
        site_name_col = _wqp_column(frame, "MonitoringLocationName")
        characteristic_col = _wqp_column(frame, "CharacteristicName")
        value_col = _wqp_column(frame, "ResultMeasureValue")
        unit_col = _wqp_column(frame, "ResultMeasure/MeasureUnitCode", "ResultMeasureUnitCode")
        method_col = _wqp_column(frame, "ResultAnalyticalMethod/MethodName", "MethodName")
        fraction_col = _wqp_column(frame, "ResultSampleFractionText")
        medium_col = _wqp_column(frame, "ActivityMediaName")
        site_type_col = _wqp_column(frame, "MonitoringLocationTypeName")
        lat_col = _wqp_column(frame, "LatitudeMeasure")
        lon_col = _wqp_column(frame, "LongitudeMeasure")
        for _, row in frame.iterrows():
            lat = pd.to_numeric(pd.Series([row.get(lat_col) if lat_col else None]), errors="coerce").iloc[0]
            lon = pd.to_numeric(pd.Series([row.get(lon_col) if lon_col else None]), errors="coerce").iloc[0]
            distance = _haversine_km(float(lat), float(lon), float(target_lat), float(target_lon)) if pd.notna(lat) and pd.notna(lon) and target_lat and target_lon else pd.NA
            characteristic = clean_text(row.get(characteristic_col)) if characteristic_col else ""
            fraction = clean_text(row.get(fraction_col)) if fraction_col else ""
            unit = clean_text(row.get(unit_col)) if unit_col else ""
            tier = "B" if "dissolved organic carbon" in characteristic.lower() and fraction.lower() in {"filtered", "dissolved"} and unit else "C"
            rows.append(
                {
                    "source_id": "wqp_usgs_yukon_candidate",
                    "site_id": clean_text(row.get(site_id_col)) if site_id_col else "",
                    "site_name": clean_text(row.get(site_name_col)) if site_name_col else "",
                    "river_target": "Yukon",
                    "characteristic": characteristic,
                    "result_value": clean_text(row.get(value_col)) if value_col else "",
                    "unit": unit,
                    "method": clean_text(row.get(method_col)) if method_col else "",
                    "filtered_or_unfiltered": fraction,
                    "medium": clean_text(row.get(medium_col)) if medium_col else "",
                    "site_type": clean_text(row.get(site_type_col)) if site_type_col else "",
                    "latitude": lat,
                    "longitude": lon,
                    "station_distance_to_target_km": distance,
                    "usability_tier": tier,
                    "notes": f"candidate-only; source_file={file.as_posix()}",
                }
            )
    return pd.DataFrame(rows, columns=QC_COLUMNS)


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    wqp = build_wqp_candidate_qc()
    datastream = pd.DataFrame(columns=QC_COLUMNS)
    wqp.to_csv(TABLE_DIR / "wqp_usgs_candidate_label_qc.csv", index=False, encoding="utf-8")
    datastream.to_csv(TABLE_DIR / "datastream_mackenzie_candidate_label_qc.csv", index=False, encoding="utf-8")
    return wqp, datastream

