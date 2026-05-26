from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests
import yaml

from .manifest import append_manifest, manifest_failure, manifest_for_file, read_manifest, sha256_file, source_by_id, utc_now
from .model_readiness import generate_model_readiness_report
from .normalize import canonical_river, load_rivers, version_from_text
from .paths import CONFIG_DIR, PROCESSED_DIR, RAW_EXTERNAL_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs, path, relpath
from .reports import generate_reports
from .schemas import ensure_columns, read_table_if_exists, write_table


WQP_SOURCE_ID = "wqp_usgs_yukon_candidate"
DATASTREAM_SOURCE_ID = "datastream_mackenzie_candidate"
ADC_SOURCE_ID = "arctic_data_center_tank_2023"
PARTNERS_SOURCE_ID = "partners_mdpi_eurasian_candidate"
NO_MODEL_TEXT = "No DOC model was trained. No DOC prediction or flux product was generated."

WQP_QC_COLUMNS = [
    "source_id",
    "organization",
    "monitoring_location_id",
    "site_name",
    "latitude",
    "longitude",
    "distance_to_target_station_km",
    "river",
    "station_comparability",
    "sample_date",
    "characteristic_name",
    "parameter_canonical",
    "original_value",
    "original_unit",
    "value_mgC_L",
    "medium",
    "fraction",
    "method",
    "activity_type",
    "result_status",
    "usability_tier",
    "can_train_doc_model",
    "can_train_daily_flux_model",
    "is_toc_not_doc",
    "exclusion_reason",
    "notes",
]

DATASTREAM_SITE_COLUMNS = [
    "Id",
    "DOI",
    "ID",
    "Name",
    "Latitude",
    "Longitude",
    "MonitoringLocationType",
]

DATASTREAM_RESULT_COLUMNS = [
    "Id",
    "LocationId",
    "DOI",
    "ActivityType",
    "ActivityMediaName",
    "ActivityStartDate",
    "CharacteristicName",
    "MethodSpeciation",
    "ResultSampleFraction",
    "ResultValue",
    "ResultUnit",
    "ResultStatusID",
    "ResultAnalyticalMethodName",
    "LaboratorySampleID",
]


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((" ".join(" ".join(self._text).split()), self._href))
            self._href = ""
            self._text = []


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_").lower() or "query"


def _write_csv(frame: pd.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    return destination


def _read_csv_if_exists(destination: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not destination.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        return pd.read_csv(destination, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame(columns=columns or [])


def _first(row: pd.Series | dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and pd.notna(row[name]) and str(row[name]) != "":
            return row[name]
    return ""


def _numeric(value: Any) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else None


def _haversine_km(lat1: Any, lon1: Any, lat2: float, lon2: float) -> float | None:
    lat = _numeric(lat1)
    lon = _numeric(lon1)
    if lat is None or lon is None:
        return None
    radius = 6371.0088
    phi1, phi2 = math.radians(lat), math.radians(lat2)
    dphi = math.radians(lat2 - lat)
    dlambda = math.radians(lon2 - lon)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_candidate_parameter(characteristic: Any, fraction: Any = "", unit: Any = "") -> tuple[str, bool, str]:
    text = f"{characteristic} {fraction}".lower()
    if "total organic carbon" in text or re.search(r"\btoc\b", text):
        return "TOC", True, ""
    if "dissolved organic carbon" in text or (("organic carbon" in text or re.search(r"\bdoc\b", text)) and "dissolved" in text):
        return "DOC", False, ""
    if "organic carbon" in text:
        return "organic_carbon_unspecified_fraction", False, "unclear_filtered_unfiltered_fraction"
    if any(token in text for token in ["uv", "absorbance", "suva", "color", "turbidity", "sediment", "temperature", "discharge", "dom", "cdom"]):
        return "proxy_or_context", False, "not_doc_label_proxy_or_context"
    return "other", False, "not_doc_label"


def _value_mg_c_l(value: Any, unit: Any) -> tuple[float | None, str]:
    parsed = _numeric(value)
    unit_text = str(unit).lower().replace(" ", "")
    if parsed is None:
        return None, "missing_or_non_numeric_value"
    if unit_text in {"mg/l", "mg/lc", "mgc/l", "mg/lasc", "mg/lc"} or ("mg" in unit_text and "/l" in unit_text):
        return parsed, ""
    if unit_text in {"ug/l", "µg/l", "μg/l"} or ("ug" in unit_text and "/l" in unit_text):
        return parsed / 1000.0, ""
    return None, "invalid_or_unhandled_unit"


def _station_comparability(site_name: str, distance_km: float | None) -> str:
    lower = site_name.lower()
    if "yukon" in lower and distance_km is not None and distance_km <= 50:
        return "mainstem_near_target"
    if "yukon" in lower and distance_km is not None and distance_km <= 200:
        return "mainstem_candidate_distance_review"
    if distance_km is not None and distance_km <= 50:
        return "near_target_location_name_review"
    return "basin_or_nonmainstem_candidate"


def _http_get(url: str, destination: Path, source_id: str, source_url: str, *, timeout: int = 90, headers: dict[str, str] | None = None) -> requests.Response | None:
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers)
        if response.status_code >= 400:
            warning = response.headers.get("Warning", "")
            raise requests.HTTPError(f"HTTP {response.status_code}; {warning}".strip(), response=response)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        append_manifest(
            manifest_for_file(
                source_id=source_id,
                source_url=source_url,
                download_url=url,
                resolved_url=response.url,
                local_path=destination,
                version_detected="live_service_query",
                license_or_citation=source_url,
            )
        )
        return response
    except Exception as exc:
        append_manifest(
            manifest_failure(
                source_id=source_id,
                source_url=source_url,
                download_url=url,
                resolved_url="",
                failure_reason=str(exc),
                local_path=destination,
                version_detected="live_service_query",
                license_or_citation=source_url,
            )
        )
        return None


def _table_metadata(file_path: Path) -> dict[str, Any]:
    row_count: int | str = ""
    date_min = ""
    date_max = ""
    river_count: int | str = ""
    try:
        if file_path.suffix.lower() == ".csv":
            frame = pd.read_csv(file_path)
            row_count = len(frame)
        elif file_path.suffix.lower() in {".xlsx", ".xls"}:
            excel = pd.ExcelFile(file_path)
            frames = []
            for sheet in excel.sheet_names:
                preview = pd.read_excel(file_path, sheet_name=sheet)
                if not preview.empty:
                    preview["_sheet"] = sheet
                    frames.append(preview)
            frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            row_count = len(frame)
        else:
            frame = pd.DataFrame()
        if not frame.empty:
            for column in frame.columns:
                if "date" in str(column).lower():
                    dates = pd.to_datetime(frame[column], errors="coerce").dropna()
                    if not dates.empty:
                        date_min = dates.min().date().isoformat()
                        date_max = dates.max().date().isoformat()
                        break
            river_cols = [column for column in frame.columns if "river" in str(column).lower() or str(column).lower() in {"_sheet", "station"}]
            if river_cols:
                river_count = int(frame[river_cols[0]].dropna().astype(str).nunique())
    except Exception:
        pass
    return {"row_count": row_count, "date_min": date_min, "date_max": date_max, "river_count": river_count}


def complete_arcticgro_archive_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = read_manifest()
    rows = []
    arcticgro = manifest[manifest["source_id"].astype(str).str.startswith("arcticgro_")].copy()
    for _, record in arcticgro.iterrows():
        source_id = str(record["source_id"])
        local_path = path(record["local_path"]) if str(record.get("local_path", "")) else Path("")
        meta = _table_metadata(local_path) if local_path.exists() and local_path.is_file() else {}
        family = "water_quality" if "water_quality" in source_id else ("absorbance" if "absorbance" in source_id else ("discharge" if "discharge" in source_id else ("spatial" if "spatial" in source_id else "metadata")))
        status = str(record.get("download_status", ""))
        if "archived" in source_id or source_id in {"arcticgro_spatial_data", "arcticgro_water_quality_flags"}:
            decision = "manual_required" if status in {"manual_required", "failed", "dry_run", ""} else "older_version_reference_only"
        elif status == "downloaded":
            decision = "current_duplicate"
        else:
            decision = "manual_required"
        rows.append(
            {
                "source_id": source_id,
                "dataset_family": family,
                "version_detected": record.get("version_detected", "") or version_from_text(record.get("file_name", "")),
                "file_name": record.get("file_name", ""),
                "sha256": record.get("sha256", ""),
                "row_count": meta.get("row_count", ""),
                "date_min": meta.get("date_min", ""),
                "date_max": meta.get("date_max", ""),
                "river_count": meta.get("river_count", ""),
                "decision": decision,
                "notes": record.get("failure_reason", "") or "Current files are authoritative; archived/manual files remain reference-only until audited.",
            }
        )
    for source_id in [
        "arcticgro_water_quality_archived",
        "arcticgro_absorbance_archived",
        "arcticgro_discharge_archived",
        "arcticgro_spatial_data",
        "arcticgro_water_quality_flags",
    ]:
        if not (arcticgro["source_id"].astype(str) == source_id).any():
            record = source_by_id(source_id)
            append_manifest(
                {
                    "source_id": source_id,
                    "source_url": record["source_url"],
                    "resolved_url": record["source_url"],
                    "download_url": record["source_url"],
                    "retrieved_at_utc": "",
                    "local_path": "",
                    "file_name": "",
                    "file_size_bytes": "",
                    "sha256": "",
                    "version_detected": "",
                    "download_status": "manual_required",
                    "failure_reason": "Archive/spatial/flags acquisition requires manual folder review or existing current workbook parsing.",
                    "license_or_citation": "ArcticGRO official data archive.",
                    "commit_raw_data": False,
                }
            )
            rows.append(
                {
                    "source_id": source_id,
                    "dataset_family": "metadata" if "flags" in source_id else source_id.replace("arcticgro_", ""),
                    "version_detected": "",
                    "file_name": "",
                    "sha256": "",
                    "row_count": "",
                    "date_min": "",
                    "date_max": "",
                    "river_count": "",
                    "decision": "manual_required",
                    "notes": "Archive/spatial/flags acquisition requires manual folder review or existing current workbook parsing.",
                }
            )
    inventory = pd.DataFrame(rows).drop_duplicates(["source_id", "file_name", "sha256"], keep="last")
    comparison = inventory.copy()
    _write_csv(inventory, TABLE_DIR / "arcticgro_archive_inventory.csv")
    _write_csv(comparison, TABLE_DIR / "arcticgro_version_comparison.csv")
    return inventory, comparison


def _wqp_query_url(service: str, params: dict[str, Any]) -> str:
    return f"https://www.waterqualitydata.us/data/{service}/search?{urlencode(params, doseq=True)}"


def complete_wqp_yukon() -> pd.DataFrame:
    record = source_by_id(WQP_SOURCE_ID)
    out_dir = path(record.get("local_subdir", "data/raw_external/wqp_usgs"))
    query_dir = out_dir / "queries"
    bbox = load_rivers()["Yukon"]["wqp_query_hints"]["bBox"]
    base_params = {
        "countrycode": "US",
        "statecode": "US:02",
        "siteType": "Stream",
        "bBox": bbox,
        "mimeType": "csv",
        "zip": "no",
    }
    station_url = _wqp_query_url("Station", base_params)
    station_path = out_dir / "yukon_sites.csv"
    _http_get(station_url, station_path, WQP_SOURCE_ID, record["source_url"])
    sites = _read_csv_if_exists(station_path)

    result_frames = []
    for characteristic in record.get("characteristics", []):
        params = {**base_params, "characteristicName": characteristic}
        url = _wqp_query_url("Result", params)
        destination = query_dir / f"{_safe_name(characteristic)}_results.csv"
        response = _http_get(url, destination, WQP_SOURCE_ID, record["source_url"])
        if response is None:
            continue
        frame = _read_csv_if_exists(destination)
        if not frame.empty:
            frame["_query_characteristic"] = characteristic
            result_frames.append(frame)
    results = pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame()
    result_path = out_dir / "yukon_results.csv"
    _write_csv(results, result_path)
    append_manifest(
        manifest_for_file(
            source_id=WQP_SOURCE_ID,
            source_url=record["source_url"],
            download_url="combined:wqp_yukon_candidate_results",
            resolved_url="combined:wqp_yukon_candidate_results",
            local_path=result_path,
            version_detected="live_service_query",
            license_or_citation="Water Quality Portal / USGS candidate data.",
        )
    )
    qc = build_wqp_candidate_qc(sites, results)
    _write_csv(qc, TABLE_DIR / "wqp_usgs_candidate_label_qc.csv")
    return qc


def build_wqp_candidate_qc(sites: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    target = load_rivers()["Yukon"]
    target_lat = float(target["approximate_station_latitude"])
    target_lon = float(target["approximate_station_longitude"])
    site_cols = {
        "MonitoringLocationIdentifier": "monitoring_location_id",
        "MonitoringLocationName": "site_name",
        "LatitudeMeasure": "latitude",
        "LongitudeMeasure": "longitude",
        "OrganizationIdentifier": "organization",
    }
    site_lookup = pd.DataFrame()
    if not sites.empty:
        available = {source: dest for source, dest in site_cols.items() if source in sites.columns}
        site_lookup = sites[list(available)].rename(columns=available)
        site_lookup = site_lookup.drop_duplicates("monitoring_location_id")
    rows = []
    if not results.empty:
        merged = results.copy()
        if not site_lookup.empty and "MonitoringLocationIdentifier" in merged.columns:
            merged = merged.merge(site_lookup, left_on="MonitoringLocationIdentifier", right_on="monitoring_location_id", how="left", suffixes=("", "_site"))
        for _, row in merged.iterrows():
            location_id = _first(row, ["MonitoringLocationIdentifier", "monitoring_location_id"])
            site_name = _first(row, ["MonitoringLocationName", "site_name"])
            latitude = _first(row, ["LatitudeMeasure", "latitude"])
            longitude = _first(row, ["LongitudeMeasure", "longitude"])
            organization = _first(row, ["OrganizationIdentifier", "organization"])
            characteristic = _first(row, ["CharacteristicName", "_query_characteristic"])
            fraction = _first(row, ["ResultSampleFractionText", "ResultSampleFraction", "MethodSpeciationText"])
            unit = _first(row, ["ResultMeasure/MeasureUnitCode", "ResultMeasure.MeasureUnitCode", "ResultUnit"])
            original_value = _first(row, ["ResultMeasureValue", "ResultMeasure/MeasureValue", "ResultValue"])
            parameter, is_toc, class_reason = classify_candidate_parameter(characteristic, fraction, unit)
            value_mg, unit_reason = _value_mg_c_l(original_value, unit) if parameter in {"DOC", "TOC", "organic_carbon_unspecified_fraction"} else (None, "")
            distance = _haversine_km(latitude, longitude, target_lat, target_lon)
            comparability = _station_comparability(str(site_name), distance)
            exclusion = ";".join(reason for reason in [class_reason, unit_reason if parameter in {"DOC", "TOC", "organic_carbon_unspecified_fraction"} else ""] if reason)
            tier = "C" if parameter == "DOC" and value_mg is not None and comparability == "mainstem_near_target" else ("D" if parameter in {"TOC", "organic_carbon_unspecified_fraction"} else "Excluded")
            can_train = tier == "C"
            if comparability != "mainstem_near_target" and parameter == "DOC":
                exclusion = ";".join(filter(None, [exclusion, "site_comparability_review_required"]))
                can_train = False
            rows.append(
                {
                    "source_id": WQP_SOURCE_ID,
                    "organization": organization,
                    "monitoring_location_id": location_id,
                    "site_name": site_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "distance_to_target_station_km": round(distance, 3) if distance is not None else "",
                    "river": "Yukon",
                    "station_comparability": comparability,
                    "sample_date": _first(row, ["ActivityStartDate"]),
                    "characteristic_name": characteristic,
                    "parameter_canonical": parameter,
                    "original_value": original_value,
                    "original_unit": unit,
                    "value_mgC_L": value_mg if value_mg is not None else "",
                    "medium": _first(row, ["ActivityMediaName"]),
                    "fraction": fraction,
                    "method": _first(row, ["ResultAnalyticalMethod/MethodName", "ResultAnalyticalMethodName"]),
                    "activity_type": _first(row, ["ActivityTypeCode", "ActivityType"]),
                    "result_status": _first(row, ["ResultStatusIdentifier", "ResultStatusID"]),
                    "usability_tier": tier,
                    "can_train_doc_model": can_train,
                    "can_train_daily_flux_model": False,
                    "is_toc_not_doc": is_toc,
                    "exclusion_reason": exclusion,
                    "notes": "WQP candidate only; not promoted by default.",
                }
            )
    return pd.DataFrame(rows, columns=WQP_QC_COLUMNS)


def _datastream_get(endpoint: str, params: dict[str, str], api_key: str) -> tuple[pd.DataFrame, str]:
    headers = {"x-api-key": api_key}
    base = f"https://api.datastream.org/v1/odata/v4/{endpoint}"
    response = requests.get(base, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()
    return pd.DataFrame(payload.get("value", [])), response.url


def complete_datastream_mackenzie() -> pd.DataFrame:
    record = source_by_id(DATASTREAM_SOURCE_ID)
    out_dir = path(record.get("local_subdir", "data/raw_external/datastream_mackenzie"))
    site_path = out_dir / "sites.csv"
    result_path = out_dir / "results.csv"
    api_key = os.environ.get("DATASTREAM_API_KEY", "")
    if not api_key:
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_csv(pd.DataFrame(columns=DATASTREAM_SITE_COLUMNS), site_path)
        _write_csv(pd.DataFrame(columns=DATASTREAM_RESULT_COLUMNS), result_path)
        append_manifest(
            manifest_failure(
                source_id=DATASTREAM_SOURCE_ID,
                source_url=record["source_url"],
                download_url="https://api.datastream.org/v1/odata/v4/Records?$filter=RegionId eq 'hub.mackenzie'",
                resolved_url=record["source_url"],
                failure_reason="DATASTREAM_API_KEY is not configured; DataStream API requires x-api-key. Manual/API-key acquisition required.",
                local_path=result_path,
                version_detected="live_api",
                license_or_citation="DataStream API; citations and licences available from /Metadata endpoint.",
            )
        )
        qc = pd.DataFrame(columns=WQP_QC_COLUMNS)
        _write_csv(qc, TABLE_DIR / "datastream_mackenzie_candidate_label_qc.csv")
        return qc

    characteristics = ["DOC", "Dissolved organic carbon", "TOC", "Total organic carbon", "CDOM", "Absorbance", "UV254", "SUVA", "Color", "Turbidity", "Suspended sediment", "Water temperature"]
    filter_text = "RegionId eq 'hub.mackenzie' and CharacteristicName in (" + ",".join(f"'{item}'" for item in characteristics) + ")"
    try:
        sites, site_url = _datastream_get(
            "Locations",
            {"$filter": "RegionId eq 'hub.mackenzie'", "$top": "10000"},
            api_key,
        )
        results, result_url = _datastream_get(
            "Observations",
            {"$filter": filter_text, "$top": "10000"},
            api_key,
        )
        _write_csv(sites, site_path)
        _write_csv(results, result_path)
        append_manifest(manifest_for_file(source_id=DATASTREAM_SOURCE_ID, source_url=record["source_url"], download_url=site_url, resolved_url=site_url, local_path=site_path, version_detected="live_api", license_or_citation="DataStream API candidate metadata."))
        append_manifest(manifest_for_file(source_id=DATASTREAM_SOURCE_ID, source_url=record["source_url"], download_url=result_url, resolved_url=result_url, local_path=result_path, version_detected="live_api", license_or_citation="DataStream API candidate observations."))
    except Exception as exc:
        append_manifest(manifest_failure(source_id=DATASTREAM_SOURCE_ID, source_url=record["source_url"], download_url="https://api.datastream.org/v1/odata/v4/Observations", failure_reason=str(exc), local_path=result_path, version_detected="live_api", license_or_citation="DataStream API candidate observations."))
        sites = pd.DataFrame(columns=DATASTREAM_SITE_COLUMNS)
        results = pd.DataFrame(columns=DATASTREAM_RESULT_COLUMNS)
        _write_csv(sites, site_path)
        _write_csv(results, result_path)
    qc = build_datastream_candidate_qc(sites, results)
    _write_csv(qc, TABLE_DIR / "datastream_mackenzie_candidate_label_qc.csv")
    return qc


def build_datastream_candidate_qc(sites: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    target = load_rivers()["Mackenzie"]
    target_lat = float(target["approximate_station_latitude"])
    target_lon = float(target["approximate_station_longitude"])
    site_lookup = sites.rename(columns={"Id": "LocationId", "Name": "site_name", "Latitude": "latitude", "Longitude": "longitude", "ID": "monitoring_location_id"}) if not sites.empty else pd.DataFrame()
    rows = []
    if not results.empty:
        merged = results.copy()
        if not site_lookup.empty and "LocationId" in merged.columns:
            merged = merged.merge(site_lookup[["LocationId", "monitoring_location_id", "site_name", "latitude", "longitude"]], on="LocationId", how="left")
        for _, row in merged.iterrows():
            characteristic = _first(row, ["CharacteristicName"])
            fraction = _first(row, ["ResultSampleFraction", "MethodSpeciation"])
            unit = _first(row, ["ResultUnit"])
            value = _first(row, ["ResultValue"])
            parameter, is_toc, class_reason = classify_candidate_parameter(characteristic, fraction, unit)
            value_mg, unit_reason = _value_mg_c_l(value, unit) if parameter in {"DOC", "TOC", "organic_carbon_unspecified_fraction"} else (None, "")
            distance = _haversine_km(row.get("latitude"), row.get("longitude"), target_lat, target_lon)
            comparability = "mainstem_candidate_distance_review" if distance is not None and distance <= 200 else "basin_or_nonmainstem_candidate"
            exclusion = ";".join(reason for reason in [class_reason, unit_reason] if reason)
            tier = "C" if parameter == "DOC" and value_mg is not None and comparability.startswith("mainstem") else ("D" if parameter in {"TOC", "organic_carbon_unspecified_fraction"} else "Excluded")
            rows.append(
                {
                    "source_id": DATASTREAM_SOURCE_ID,
                    "organization": _first(row, ["DOI"]),
                    "monitoring_location_id": _first(row, ["monitoring_location_id", "LocationId"]),
                    "site_name": _first(row, ["site_name"]),
                    "latitude": row.get("latitude", ""),
                    "longitude": row.get("longitude", ""),
                    "distance_to_target_station_km": round(distance, 3) if distance is not None else "",
                    "river": "Mackenzie",
                    "station_comparability": comparability,
                    "sample_date": _first(row, ["ActivityStartDate"]),
                    "characteristic_name": characteristic,
                    "parameter_canonical": parameter,
                    "original_value": value,
                    "original_unit": unit,
                    "value_mgC_L": value_mg if value_mg is not None else "",
                    "medium": _first(row, ["ActivityMediaName"]),
                    "fraction": fraction,
                    "method": _first(row, ["ResultAnalyticalMethodName"]),
                    "activity_type": _first(row, ["ActivityType"]),
                    "result_status": _first(row, ["ResultStatusID"]),
                    "usability_tier": tier,
                    "can_train_doc_model": tier == "C",
                    "can_train_daily_flux_model": False,
                    "is_toc_not_doc": is_toc,
                    "exclusion_reason": exclusion,
                    "notes": "DataStream candidate only; not promoted by default.",
                }
            )
    return pd.DataFrame(rows, columns=WQP_QC_COLUMNS)


def complete_arctic_data_center_inventory() -> pd.DataFrame:
    record = source_by_id(ADC_SOURCE_ID)
    out_dir = path(record.get("local_subdir", "data/raw_external/arctic_data_center/tank_2023"))
    landing = out_dir / "doi_landing_page.html"
    response = _http_get(record["source_url"], landing, ADC_SOURCE_ID, record["source_url"], timeout=90)
    rows = []
    if response is not None:
        parser = _LinkParser()
        parser.feed(response.text)
        links = [(text, href) for text, href in parser.links if href]
        if links:
            for text, href in links[:200]:
                if any(token in href.lower() for token in ["object", "download", "metacat", "data", "resource_map"]):
                    rows.append(
                        {
                            "file_name": text or Path(href).name,
                            "file_url": href,
                            "file_size": "",
                            "data_role": "benchmark_or_validation",
                            "download_status": "indexed",
                            "failure_reason": "",
                            "candidate_use": "benchmark_or_validation",
                            "notes": "Indexed from DOI landing page; not merged into labels.",
                        }
                    )
        if not rows:
            rows.append({"file_name": landing.name, "file_url": response.url, "file_size": landing.stat().st_size if landing.exists() else "", "data_role": "benchmark_or_validation", "download_status": "landing_page_saved", "failure_reason": "", "candidate_use": "benchmark_or_validation", "notes": "Landing page saved; package member parsing requires manual DataONE/EML follow-up."})
    else:
        rows.append({"file_name": "", "file_url": record["source_url"], "file_size": "", "data_role": "benchmark_or_validation", "download_status": "manual_required", "failure_reason": "DOI landing page request failed; manual acquisition required.", "candidate_use": "benchmark_or_validation", "notes": "Do not merge into training labels until duplicate/provenance audit."})
    inventory = pd.DataFrame(rows)
    _write_csv(inventory, TABLE_DIR / "arctic_data_center_tank_2023_inventory.csv")
    return inventory


def complete_partners_mdpi_inventory() -> tuple[pd.DataFrame, pd.DataFrame]:
    record = source_by_id(PARTNERS_SOURCE_ID)
    out_dir = path(record.get("local_subdir", "data/raw_external/partners_mdpi"))
    article_url = "https://www.mdpi.com/2073-4441/16/2/316"
    supplement_url = "https://www.mdpi.com/article/10.3390/w16020316/s1"
    rows = []
    qc_rows: list[dict[str, Any]] = []
    for url, name in [(article_url, "mdpi_2024_water_16_316_article.html"), (supplement_url, "mdpi_2024_water_16_316_supplement")]:
        destination = out_dir / name
        response = _http_get(url, destination, PARTNERS_SOURCE_ID, record["source_url"], timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        rows.append(
            {
                "file_name": destination.name,
                "file_url": url,
                "download_status": "downloaded" if response is not None else "manual_required",
                "failure_reason": "" if response is not None else "Automated MDPI request failed or was denied; manual supplement acquisition required.",
                "candidate_use": "supplementary mechanism / possible label source after deduplication",
                "notes": "Target article: Water 2024, 16(2), 316; supplement Table S1(1-4).",
            }
        )
    inventory = pd.DataFrame(rows)
    qc = pd.DataFrame(qc_rows, columns=WQP_QC_COLUMNS)
    _write_csv(inventory, TABLE_DIR / "partners_mdpi_supplement_inventory.csv")
    _write_csv(qc, TABLE_DIR / "partners_mdpi_candidate_label_qc.csv")
    return inventory, qc


def complete_hydrobasins_status() -> pd.DataFrame:
    local_config = CONFIG_DIR / "local_paths.yaml"
    local_paths = yaml.safe_load(local_config.read_text(encoding="utf-8")) if local_config.exists() else {}
    rows = []
    status = "placeholder_only"
    for source_id in ["hydrobasins", "hydroatlas"]:
        record = source_by_id(source_id)
        configured = ((local_paths or {}).get(source_id, {}) or {}).get("local_path", "")
        exists = bool(configured and Path(configured).exists())
        row_status = "local_path_configured" if exists else "manual_required"
        rows.append(
            {
                "source_id": source_id,
                "source_url": record["source_url"],
                "local_path": configured,
                "local_path_exists": exists,
                "download_status": row_status,
                "basin_context_status": "complete" if exists else "placeholder_only",
                "failure_reason": "" if exists else "Large HydroBASINS/HydroATLAS files require manual download and configs/local_paths.yaml.",
                "notes": "Basin context is not DOC label data.",
            }
        )
        if exists:
            status = "manual_required"
    current = read_table_if_exists("basin_context_canonical")
    if current.empty:
        from .preprocess import basin_context

        current = basin_context.run()
    current = ensure_columns(current, "basin_context_canonical")
    if "quality_flag" not in current.columns or current["quality_flag"].fillna("").eq("").all():
        current["quality_flag"] = "placeholder_only"
    write_table(current, "basin_context_canonical", PROCESSED_DIR / "basin_context_canonical.csv")
    table = pd.DataFrame(rows)
    table["overall_basin_context_status"] = "complete" if all(table["local_path_exists"]) else status
    _write_csv(table, TABLE_DIR / "hydrobasins_hydroatlas_acquisition_status.csv")
    return table


def generate_gee_extraction_plan() -> pd.DataFrame:
    optical = read_table_if_exists("optical_timeseries_canonical")
    hydro = read_table_if_exists("daily_hydroclimate_canonical")
    aux = read_table_if_exists("auxiliary_context_canonical")
    rows = []
    specs = [
        ("gee_hls_s30_l30", "NASA/HLS/HLSS30/v002;NASA/HLS/HLSL30/v002", "HLS", "2016-2025", "optical_timeseries_canonical", "high"),
        ("gee_sentinel2_sr_harmonized", "COPERNICUS/S2_SR_HARMONIZED", "Sentinel-2", "2017-2025", "optical_timeseries_canonical", "high"),
        ("gee_landsat_c2_l2", "LANDSAT/LT05/C02/T1_L2;LANDSAT/LE07/C02/T1_L2;LANDSAT/LC08/C02/T1_L2;LANDSAT/LC09/C02/T1_L2", "Landsat", "2003-2025", "optical_timeseries_canonical", "medium"),
        ("gee_era5_land", "ECMWF/ERA5_LAND/HOURLY", "ERA5-Land", "2000-2025", "daily_hydroclimate_canonical", "high"),
        ("gee_modis_mod10a1", "MODIS/061/MOD10A1", "MODIS snow", "2000-2025", "daily_hydroclimate_canonical", "high"),
        ("gee_smap_context_optional", "NASA/SMAP/SPL3SMP_E/006", "SMAP", "2015-2025", "auxiliary_context_canonical", "optional"),
    ]
    for source_id, collection, sensor, years, table, priority in specs:
        for river in load_rivers():
            if table == "optical_timeseries_canonical" and not optical.empty:
                existing = optical[(optical["river"].astype(str) == river) & (optical["sensor"].astype(str).str.contains(sensor.split()[0], case=False, na=False))]
                legacy = existing[existing["source_id"].astype(str).str.contains("old_arctic_doc_snowmelt_untrained_data", na=False)]
            elif table == "daily_hydroclimate_canonical" and not hydro.empty:
                existing = hydro[hydro["river"].astype(str) == river]
                legacy = existing[existing["source_id"].astype(str).str.contains("old_arctic_doc_snowmelt_untrained_data", na=False)]
            elif table == "auxiliary_context_canonical" and not aux.empty:
                existing = aux[aux["river"].astype(str) == river]
                legacy = existing[existing["source_id"].astype(str).str.contains("old_arctic_doc_snowmelt_untrained_data", na=False)]
            else:
                legacy = pd.DataFrame()
            command_source = "gee_optical" if table == "optical_timeseries_canonical" else "gee_hydroclimate"
            rows.append(
                {
                    "source_id": source_id,
                    "collection": collection,
                    "river": river,
                    "years": years,
                    "roi_set": "final_primary",
                    "existing_legacy_rows": len(legacy),
                    "needs_regeneration": True,
                    "priority": priority,
                    "estimated_output_table": table,
                    "command": f"python -m arctic_doc_data_audit.cli download --source {command_source} --rivers {river} --years {years} --roi-set final_primary --report-only",
                    "blocking_reason": "Earth Engine authentication/extraction not run in data completion phase; legacy rows require regeneration audit.",
                }
            )
    plan = pd.DataFrame(rows)
    _write_csv(plan, TABLE_DIR / "gee_extraction_plan.csv")
    lines = [
        "# GEE Extraction Readiness Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Summary",
        "Legacy HLS/Sentinel-2/ERA5/MODIS/SMAP rows are useful for audit continuity, but the new project should regenerate GEE products before full training.",
        "",
        plan.groupby(["source_id", "estimated_output_table"], dropna=False).agg(existing_legacy_rows=("existing_legacy_rows", "sum"), planned_river_tasks=("river", "count")).reset_index().to_markdown(index=False),
        "",
        "## Extraction Plan",
        plan.to_markdown(index=False),
    ]
    (REPORT_DIR / "gee_extraction_readiness_report.md").write_text("\n".join(lines), encoding="utf-8")
    return plan


def complete_data_sources(all_sources: bool = True) -> None:
    ensure_project_dirs()
    complete_arcticgro_archive_audit()
    complete_wqp_yukon()
    complete_datastream_mackenzie()
    complete_arctic_data_center_inventory()
    complete_partners_mdpi_inventory()
    complete_hydrobasins_status()
    generate_gee_extraction_plan()
    generate_reports()


def _read_candidate_tables() -> pd.DataFrame:
    frames = []
    for name in ["wqp_usgs_candidate_label_qc.csv", "datastream_mackenzie_candidate_label_qc.csv", "partners_mdpi_candidate_label_qc.csv"]:
        frame = _read_csv_if_exists(TABLE_DIR / name, WQP_QC_COLUMNS)
        if not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=WQP_QC_COLUMNS)


def audit_candidate_labels(promote_approved: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidates = _read_candidate_tables()
    labels = read_table_if_exists("doc_labels_canonical")
    labels_doc = labels[labels["parameter_canonical"].astype(str) == "DOC"].copy() if not labels.empty else pd.DataFrame()
    decisions = [
        {
            "candidate_source_id": "",
            "candidate_row_id": "priority_rule",
            "river": "",
            "site_or_station": "",
            "date": "",
            "parameter_canonical": "DOC",
            "matched_label_id": "",
            "matched_source_id": "arcticgro_water_quality_current",
            "decision": "arcticgro_current_preferred",
            "notes": "Tier A ArcticGRO current DOC is preferred over external/reference duplicate candidates.",
        }
    ]
    plans = []
    for idx, row in candidates.iterrows():
        river = str(row.get("river", ""))
        date = str(row.get("sample_date", ""))
        parameter = str(row.get("parameter_canonical", ""))
        label_match = labels_doc[(labels_doc["river"].astype(str) == river) & (labels_doc["date"].astype(str) == date)] if not labels_doc.empty and parameter == "DOC" else pd.DataFrame()
        if not label_match.empty:
            decision = "duplicate_external_loses_to_arcticgro_current"
            matched_label = str(label_match.iloc[0].get("label_id", ""))
            matched_source = str(label_match.iloc[0].get("source_id", ""))
        elif parameter == "DOC" and str(row.get("usability_tier", "")) == "C":
            decision = "candidate_new_requires_review"
            matched_label = ""
            matched_source = ""
        elif parameter == "TOC":
            decision = "toc_sensitivity_only"
            matched_label = ""
            matched_source = ""
        else:
            decision = "excluded_or_context_only"
            matched_label = ""
            matched_source = ""
        decisions.append(
            {
                "candidate_source_id": row.get("source_id", ""),
                "candidate_row_id": idx,
                "river": river,
                "site_or_station": row.get("site_name", ""),
                "date": date,
                "parameter_canonical": parameter,
                "matched_label_id": matched_label,
                "matched_source_id": matched_source,
                "decision": decision,
                "notes": row.get("exclusion_reason", ""),
            }
        )
        approved = bool(promote_approved and decision == "candidate_new_requires_review")
        plans.append(
            {
                "candidate_source_id": row.get("source_id", ""),
                "candidate_row_id": idx,
                "river": river,
                "date": date,
                "parameter_canonical": parameter,
                "usability_tier": row.get("usability_tier", ""),
                "approved_for_promotion": approved,
                "promotion_action": "promote_to_doc_labels_canonical" if approved else "review_required_no_default_promotion",
                "decision": decision,
                "notes": "Default audit does not promote candidates." if not approved else "Explicit --promote-approved used.",
            }
        )
    summary = candidates.groupby(["source_id", "parameter_canonical", "usability_tier"], dropna=False).size().reset_index(name="candidate_rows") if not candidates.empty else pd.DataFrame(columns=["source_id", "parameter_canonical", "usability_tier", "candidate_rows"])
    decisions_frame = pd.DataFrame(decisions)
    plan = pd.DataFrame(plans)
    _write_csv(summary, TABLE_DIR / "candidate_label_audit_summary.csv")
    _write_csv(decisions_frame, TABLE_DIR / "candidate_label_duplicate_decisions.csv")
    _write_csv(plan, TABLE_DIR / "candidate_label_promotion_plan.csv")
    if promote_approved and not plan.empty and plan["approved_for_promotion"].any():
        # Placeholder for future explicit promotion. This branch is intentionally conservative.
        pass
    generate_reports()
    return summary, decisions_frame, plan


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path(), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _run_tests_for_freeze() -> tuple[bool, str]:
    try:
        result = subprocess.run([sys.executable, "-m", "pytest"], cwd=path(), text=True, capture_output=True, timeout=300)
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return result.returncode == 0, output.strip()
    except Exception as exc:
        return False, str(exc)


def _canonical_hashes() -> pd.DataFrame:
    rows = []
    for file_path in sorted(PROCESSED_DIR.glob("*.csv")):
        try:
            frame = pd.read_csv(file_path)
            row_count = len(frame)
        except Exception:
            row_count = ""
        rows.append({"table_name": file_path.stem, "local_path": relpath(file_path), "row_count": row_count, "sha256": sha256_file(file_path)})
    table = pd.DataFrame(rows)
    _write_csv(table, TABLE_DIR / "data_freeze_canonical_hashes.csv")
    return table


def freeze_data(freeze_id: str, run_tests: bool = False) -> Path:
    ensure_project_dirs()
    generate_model_readiness_report()
    canonical_hashes = _canonical_hashes()
    manifest = read_manifest()
    freeze_manifest = manifest.copy()
    freeze_manifest.insert(0, "freeze_id", freeze_id)
    _write_csv(freeze_manifest, TABLE_DIR / "data_freeze_manifest.csv")
    source_status = manifest.groupby(["source_id", "download_status"], dropna=False).size().reset_index(name="records") if not manifest.empty else pd.DataFrame(columns=["source_id", "download_status", "records"])
    _write_csv(source_status, TABLE_DIR / "data_freeze_source_status.csv")

    model_report_exists = (REPORT_DIR / "model_readiness_report.md").exists()
    gee_plan_exists = (TABLE_DIR / "gee_extraction_plan.csv").exists()
    candidate_audit_exists = (TABLE_DIR / "candidate_label_audit_summary.csv").exists()
    basin_status = _read_csv_if_exists(TABLE_DIR / "hydrobasins_hydroatlas_acquisition_status.csv")
    basin_context_status = "unknown"
    if not basin_status.empty:
        basin_context_status = str(basin_status.get("overall_basin_context_status", pd.Series(["unknown"])).iloc[0])
    tests_passed = False
    test_output = "Tests were not run inside freeze-data."
    if run_tests:
        tests_passed, test_output = _run_tests_for_freeze()
        (REPORT_DIR / "test_report.md").write_text(
            "# Test Report\n\n"
            f"Generated: {utc_now()}\n\n"
            f"{NO_MODEL_TEXT}\n\n"
            "## Result\n\n"
            "```text\n"
            f"{test_output.splitlines()[-1] if test_output else 'no output'}\n"
            "```\n",
            encoding="utf-8",
        )
    else:
        existing_test_report = REPORT_DIR / "test_report.md"
        if existing_test_report.exists():
            text = existing_test_report.read_text(encoding="utf-8", errors="replace").lower()
            tests_passed = "passed" in text and "failed" not in text
            test_output = "Inferred from existing test_report.md."

    row_counts = {row["table_name"]: int(row["row_count"]) if str(row["row_count"]).isdigit() else row["row_count"] for _, row in canonical_hashes.iterrows()}
    blockers = []
    if not gee_plan_exists:
        blockers.append("GEE extraction readiness plan missing.")
    if not candidate_audit_exists:
        blockers.append("Candidate label audit missing.")
    if basin_context_status in {"placeholder_only", "unknown"}:
        blockers.append(f"Basin context status is {basin_context_status}.")
    if not tests_passed:
        blockers.append("Tests have not passed for this freeze.")

    baseline_ready = (
        row_counts.get("doc_labels_canonical", 0)
        and row_counts.get("daily_discharge_canonical", 0)
        and row_counts.get("daily_hydroclimate_canonical", 0)
        and model_report_exists
        and tests_passed
    )
    full_ready = baseline_ready and candidate_audit_exists and gee_plan_exists and basin_context_status == "complete" and not blockers
    lines = [
        "# Data Freeze Report",
        "",
        f"freeze_id: `{freeze_id}`",
        f"generated_at: `{utc_now()}`",
        f"git_commit: `{_git_commit()}`",
        "",
        NO_MODEL_TEXT,
        "",
        "## Freeze Readiness",
        f"- READY_FOR_BASELINE_TRAINING: `{bool(baseline_ready)}`",
        f"- READY_FOR_FULL_TRAINING: `{bool(full_ready)}`",
        f"- frozen_data_training_status: `{'ready_for_baseline_not_full' if baseline_ready and not full_ready else ('ready_for_full_training' if full_ready else 'not_ready')}`",
        "",
        "## Source Status Summary",
        source_status.to_markdown(index=False) if not source_status.empty else "_No manifest rows._",
        "",
        "## Canonical Table Hashes",
        canonical_hashes.to_markdown(index=False),
        "",
        "## Candidate Source Completion",
        f"- candidate_label_audit_completed: `{candidate_audit_exists}`",
        f"- gee_extraction_readiness_completed: `{gee_plan_exists}`",
        f"- basin_context_status: `{basin_context_status}`",
        "",
        "## Model Readiness Summary",
        "- See `outputs/reports/model_readiness_report.md`.",
        f"- model_readiness_exists: `{model_report_exists}`",
        "",
        "## Test Status",
        f"- tests_passed: `{tests_passed}`",
        f"- test_summary: `{test_output.splitlines()[-1] if test_output else ''}`",
        "",
        "## Unresolved Blockers",
        "\n".join(f"- {item}" for item in blockers) if blockers else "_No critical blockers._",
        "",
        "## Explicit Statement",
        "Frozen data are ready for baseline training only if the readiness flag above is true. Full training must wait until all candidate sources and basin/GEE regeneration blockers are resolved.",
    ]
    out = REPORT_DIR / "data_freeze_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
