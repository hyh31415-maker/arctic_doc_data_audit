from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .manifest import append_manifest, manifest_failure, manifest_for_file, sha256_file, source_by_id, utc_now
from .normalize import load_rivers
from .paths import PROCESSED_DIR, RAW_EXTERNAL_DIR, REPORT_DIR, TABLE_DIR, path, relpath
from .schemas import ensure_columns, read_table_if_exists, write_table


LEGACY_SOURCE = "old_arctic_doc_snowmelt_untrained_data"
REGENERATED_QUALITY = "regenerated_gee"
INTERIM_GEE_DIR = path("data", "interim", "gee_regenerated")
OPTICAL_SCHEMA = "optical_timeseries_canonical"
HYDRO_SCHEMA = "daily_hydroclimate_canonical"
AUX_SCHEMA = "auxiliary_context_canonical"


@dataclass(frozen=True)
class GeeInit:
    ok: bool
    ee: Any = None
    error: str = ""
    project_id: str = ""


def _import_ee() -> GeeInit:
    try:
        import ee  # type: ignore

        try:
            ee.Initialize()
        except TypeError:
            ee.Initialize(project=None)
        except Exception:
            ee.Initialize()
        project_id = ""
        try:
            project_id = ee.data.getCloudApiUserProject() or ""
        except Exception:
            project_id = ""
        return GeeInit(ok=True, ee=ee, project_id=project_id)
    except Exception as exc:
        return GeeInit(ok=False, error=f"{type(exc).__name__}: {exc}")


def _credential_committed_check() -> str:
    project_credentials = [p for p in path().rglob("credentials") if ".git" not in p.parts]
    return "WARNING_project_credentials_file_found" if project_credentials else "ok_not_in_project_tree"


def gee_auth_check() -> pd.DataFrame:
    init = _import_ee()
    can_access = False
    test_collection = "ECMWF/ERA5_LAND/HOURLY"
    error = init.error
    if init.ok:
        try:
            can_access = bool(init.ee.ImageCollection(test_collection).limit(1).size().getInfo() >= 0)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    row = {
        "checked_at_utc": utc_now(),
        "ee_initialized": init.ok,
        "project_id": init.project_id,
        "auth_method_detected": "earthengine_default_credentials" if init.ok else "unavailable",
        "can_access_test_collection": can_access,
        "test_collection": test_collection,
        "error_message": error,
        "credential_committed_to_git_check": _credential_committed_check(),
    }
    frame = pd.DataFrame([row])
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(TABLE_DIR / "gee_auth_check.csv", index=False, encoding="utf-8")
    lines = [
        "# GEE Auth Check Report",
        "",
        f"Generated: {row['checked_at_utc']}",
        "",
        "No DOC model was trained. No DOC prediction or flux product was generated.",
        "",
        frame.to_markdown(index=False),
        "",
        "Credentials are not printed in this report.",
    ]
    (REPORT_DIR / "gee_auth_check_report.md").write_text("\n".join(lines), encoding="utf-8")
    return frame


def _parse_years(years: str) -> list[int]:
    if not years:
        return []
    if "-" in years:
        start, end = years.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part.strip()) for part in years.split(",") if part.strip()]


def _selected_rivers(rivers: str) -> list[str]:
    if not rivers or rivers.lower() == "all":
        return list(load_rivers())
    wanted = [part.strip() for part in rivers.split(",") if part.strip()]
    known = load_rivers()
    return [river for river in known if river.lower() in {item.lower() for item in wanted}]


def _roi_geojson_path(river: str, roi_set: str) -> Path | None:
    roi = read_table_if_exists("roi_catalog")
    if roi.empty:
        return None
    matches = roi[(roi["river"].astype(str) == river) & (roi["roi_set"].astype(str) == roi_set)]
    if matches.empty:
        matches = roi[(roi["river"].astype(str) == river) & (roi["roi_set"].astype(str) == "final_primary")]
    if matches.empty:
        return None
    candidate = path(matches.iloc[0].get("roi_path", ""))
    return candidate if candidate.exists() else None


def _ee_geometry(ee: Any, river: str, roi_set: str) -> Any:
    roi_path = _roi_geojson_path(river, roi_set)
    if not roi_path:
        meta = load_rivers()[river]
        lon = float(meta["approximate_station_longitude"])
        lat = float(meta["approximate_station_latitude"])
        return ee.Geometry.Point([lon, lat]).buffer(3000).bounds()
    data = json.loads(roi_path.read_text(encoding="utf-8"))
    features = data.get("features") or []
    geom = features[0].get("geometry") if features else data.get("geometry", data)
    return ee.Geometry(geom)


def _write_chunk(frame: pd.DataFrame, source_id: str, source_name: str, river: str, year: int) -> Path:
    destination = INTERIM_GEE_DIR / source_name / river / f"{year}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    record = source_by_id(source_id)
    append_manifest(
        manifest_for_file(
            source_id=source_id,
            source_url=record["source_url"],
            download_url=f"earthengine:{source_name}:{river}:{year}",
            resolved_url=f"earthengine:{source_name}:{river}:{year}",
            local_path=destination,
            version_detected=str(year),
            license_or_citation=record.get("notes", ""),
        )
    )
    return destination


def _manifest_failure(source_id: str, source_name: str, river: str, year: int | str, reason: str) -> None:
    record = source_by_id(source_id)
    append_manifest(
        manifest_failure(
            source_id=source_id,
            source_url=record["source_url"],
            download_url=f"earthengine:{source_name}:{river}:{year}",
            resolved_url=f"earthengine:{source_name}:{river}:{year}",
            failure_reason=reason,
            version_detected=str(year),
            license_or_citation=record.get("notes", ""),
        )
    )


def _feature_collection_rows(collection: Any) -> list[dict[str, Any]]:
    info = collection.getInfo()
    rows = []
    for feature in info.get("features", []):
        rows.append(feature.get("properties", {}) or {})
    return rows


def _constant_total_count(ee: Any, geom: Any, scale: int) -> Any:
    return ee.Image.constant(1).rename("total").reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geom,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).get("total")


def _optical_feature(ee: Any, image: Any, geom: Any, scale: int, source_id: str, sensor: str, collection_id: str, band_map: dict[str, str], qa_kind: str, roi_set: str, river: str) -> Any:
    src = list(band_map)
    dst = [band_map[key] for key in src]
    optical = image.select(src, dst)
    if qa_kind in {"hls", "sentinel2"}:
        optical = optical.multiply(0.0001)
    elif qa_kind == "landsat":
        optical = optical.multiply(0.0000275).add(-0.2)

    ndwi = optical.normalizedDifference(["green", "nir"]).rename("ndwi")
    mndwi = optical.normalizedDifference(["green", "swir1"]).rename("mndwi")
    red_green = optical.select("red").divide(optical.select("green")).rename("red_green_ratio")
    green_blue = optical.select("green").divide(optical.select("blue")).rename("green_blue_ratio")

    if qa_kind == "hls":
        fmask = image.select("Fmask")
        clear = fmask.bitwiseAnd(2).eq(0).And(fmask.bitwiseAnd(4).eq(0)).And(fmask.bitwiseAnd(8).eq(0)).And(fmask.bitwiseAnd(16).eq(0))
        water = fmask.bitwiseAnd(32).gt(0).Or(ndwi.gt(0.05)).Or(mndwi.gt(0.05))
        mask_method = "HLS Fmask bits 1-4 removed; Fmask water bit and NDWI/MNDWI water checks used."
    elif qa_kind == "sentinel2":
        scl = image.select("SCL")
        clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
        water = scl.eq(6).Or(ndwi.gt(0.05)).Or(mndwi.gt(0.05))
        mask_method = "Sentinel-2 SCL cloud/shadow/snow classes removed; SCL water and NDWI/MNDWI water checks used."
    else:
        qa = image.select("QA_PIXEL")
        clear = qa.bitwiseAnd(2).eq(0).And(qa.bitwiseAnd(8).eq(0)).And(qa.bitwiseAnd(16).eq(0)).And(qa.bitwiseAnd(32).eq(0))
        water = qa.bitwiseAnd(128).gt(0).Or(ndwi.gt(0.05)).Or(mndwi.gt(0.05))
        mask_method = "Landsat C2 QA_PIXEL cloud/shadow/snow bits removed; QA water bit and NDWI/MNDWI water checks used."

    valid = clear.And(water).rename("valid_water")
    stack = optical.addBands([ndwi, mndwi, red_green, green_blue]).updateMask(valid)
    stats = stack.reduceRegion(
        reducer=ee.Reducer.median().combine(ee.Reducer.count(), "", True),
        geometry=geom,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    )
    valid_count = ee.Image.constant(1).updateMask(valid).rename("valid").reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geom,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True,
    ).get("valid")
    total_count = _constant_total_count(ee, geom, scale)
    date = ee.Date(image.get("system:time_start"))
    props = ee.Dictionary(
        {
            "river": river,
            "date": date.format("YYYY-MM-dd"),
            "datetime": date.format("YYYY-MM-dd'T'HH:mm:ss"),
            "sensor": sensor,
            "collection": collection_id,
            "processing_level": "regenerated_gee",
            "roi_set": roi_set,
            "pixel_size_m": scale,
            "n_valid_water_pixels": valid_count,
            "n_total_pixels": total_count,
            "cloud_snow_water_mask_method": mask_method,
            "image_id": image.id(),
            "source_id": source_id,
            "quality_flag": REGENERATED_QUALITY,
            "snapshot_path": "",
            "original_relative_path": "",
            "sha256": "",
            "notes": f"Regenerated from Earth Engine collection {collection_id}; ROI set {roi_set}.",
        }
    )
    return ee.Feature(
        None,
        ee.Dictionary(stats).combine(props, overwrite=True),
    )


def _clean_optical_rows(rows: list[dict[str, Any]], source_id: str) -> pd.DataFrame:
    out = []
    for row in rows:
        valid = pd.to_numeric(pd.Series([row.get("n_valid_water_pixels")]), errors="coerce").iloc[0]
        total = pd.to_numeric(pd.Series([row.get("n_total_pixels")]), errors="coerce").iloc[0]
        pct = 100.0 * valid / total if pd.notna(valid) and pd.notna(total) and total else pd.NA
        out.append(
            {
                "river": row.get("river", ""),
                "date": row.get("date", ""),
                "datetime": row.get("datetime", ""),
                "sensor": row.get("sensor", ""),
                "collection": row.get("collection", ""),
                "processing_level": row.get("processing_level", "regenerated_gee"),
                "roi_set": row.get("roi_set", ""),
                "pixel_size_m": row.get("pixel_size_m", ""),
                "blue": row.get("blue_median", ""),
                "green": row.get("green_median", ""),
                "red": row.get("red_median", ""),
                "nir": row.get("nir_median", ""),
                "swir1": row.get("swir1_median", ""),
                "swir2": row.get("swir2_median", ""),
                "ndwi": row.get("ndwi_median", ""),
                "mndwi": row.get("mndwi_median", ""),
                "red_green_ratio": row.get("red_green_ratio_median", ""),
                "green_blue_ratio": row.get("green_blue_ratio_median", ""),
                "n_valid_water_pixels": row.get("n_valid_water_pixels", ""),
                "n_total_pixels": row.get("n_total_pixels", ""),
                "pct_valid_water_pixels": pct,
                "cloud_snow_water_mask_method": row.get("cloud_snow_water_mask_method", ""),
                "image_id": row.get("image_id", ""),
                "source_id": source_id,
                "quality_flag": REGENERATED_QUALITY,
                "snapshot_path": "",
                "original_relative_path": "",
                "sha256": "",
                "notes": row.get("notes", ""),
            }
        )
    frame = ensure_columns(pd.DataFrame(out), OPTICAL_SCHEMA)
    if not frame.empty:
        frame = frame.drop_duplicates(["river", "date", "datetime", "image_id", "roi_set", "sensor"], keep="last")
    return frame


def _append_optical(regenerated: pd.DataFrame) -> pd.DataFrame:
    existing_path = PROCESSED_DIR / "optical_timeseries_canonical.csv"
    existing = read_table_if_exists(OPTICAL_SCHEMA)
    existing = ensure_columns(existing, OPTICAL_SCHEMA)
    if regenerated.empty:
        return existing
    regen_sources = set(regenerated["source_id"].astype(str))
    non_same = existing[~existing["source_id"].astype(str).isin(regen_sources)]
    combined = pd.concat([non_same, regenerated], ignore_index=True)
    combined = combined.drop_duplicates(["river", "date", "datetime", "image_id", "roi_set", "sensor", "source_id"], keep="last")
    write_table(ensure_columns(combined, OPTICAL_SCHEMA), OPTICAL_SCHEMA, existing_path)
    return ensure_columns(combined, OPTICAL_SCHEMA)


def extract_optical_source(source: str, rivers: str, years: str, roi_set: str) -> pd.DataFrame:
    init = _import_ee()
    if not init.ok:
        source_id = _source_id_for_gee_source(source)
        for river in _selected_rivers(rivers):
            for year in _parse_years(years):
                _manifest_failure(source_id, source, river, year, init.error)
        return pd.DataFrame()
    ee = init.ee
    specs = _optical_specs(source)
    all_frames = []
    summary_rows = []
    for river in _selected_rivers(rivers):
        geom = _ee_geometry(ee, river, roi_set)
        for year in _parse_years(years):
            year_rows = []
            for spec in specs:
                try:
                    collection = (
                        ee.ImageCollection(spec["collection"])
                        .filterBounds(geom)
                        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
                    )
                    feature_collection = collection.map(
                        lambda image, spec=spec: _optical_feature(
                            ee,
                            image,
                            geom,
                            spec["scale"],
                            spec["source_id"],
                            spec["sensor"],
                            spec["collection"],
                            spec["band_map"],
                            spec["qa_kind"],
                            roi_set,
                            river,
                        )
                    )
                    rows = _feature_collection_rows(feature_collection)
                    year_rows.extend(rows)
                except Exception as exc:
                    _manifest_failure(spec["source_id"], source, river, year, f"{type(exc).__name__}: {exc}")
                    summary_rows.append({"source_id": spec["source_id"], "river": river, "year": year, "collection": spec["collection"], "rows": 0, "status": "failed", "failure_reason": f"{type(exc).__name__}: {exc}"})
            frame = _clean_optical_rows(year_rows, specs[0]["source_id"] if specs else "")
            if not frame.empty:
                chunk = _write_chunk(frame, specs[0]["source_id"], source, river, year)
                frame["original_relative_path"] = relpath(chunk)
                frame["sha256"] = sha256_file(chunk)
                all_frames.append(frame)
            summary_rows.append({"source_id": specs[0]["source_id"], "river": river, "year": year, "collection": ";".join(spec["collection"] for spec in specs), "rows": len(frame), "status": "downloaded" if not frame.empty else "empty", "failure_reason": ""})
    regenerated = pd.concat(all_frames, ignore_index=True) if all_frames else ensure_columns(pd.DataFrame(), OPTICAL_SCHEMA)
    _append_optical(regenerated)
    _write_extraction_summary(source, summary_rows, regenerated)
    return regenerated


def _optical_specs(source: str) -> list[dict[str, Any]]:
    if source == "hls":
        return [
            {
                "source_id": "gee_hls_s30_l30",
                "collection": "NASA/HLS/HLSS30/v002",
                "sensor": "HLS",
                "scale": 30,
                "qa_kind": "hls",
                "band_map": {"B2": "blue", "B3": "green", "B4": "red", "B8A": "nir", "B11": "swir1", "B12": "swir2"},
            },
            {
                "source_id": "gee_hls_s30_l30",
                "collection": "NASA/HLS/HLSL30/v002",
                "sensor": "HLS",
                "scale": 30,
                "qa_kind": "hls",
                "band_map": {"B2": "blue", "B3": "green", "B4": "red", "B5": "nir", "B6": "swir1", "B7": "swir2"},
            },
        ]
    if source == "sentinel2":
        return [
            {
                "source_id": "gee_sentinel2_sr_harmonized",
                "collection": "COPERNICUS/S2_SR_HARMONIZED",
                "sensor": "Sentinel-2",
                "scale": 10,
                "qa_kind": "sentinel2",
                "band_map": {"B2": "blue", "B3": "green", "B4": "red", "B8": "nir", "B11": "swir1", "B12": "swir2"},
            }
        ]
    if source == "landsat_c2":
        return [
            {
                "source_id": "gee_landsat_c2_l2",
                "collection": "LANDSAT/LT05/C02/T1_L2",
                "sensor": "Landsat",
                "scale": 30,
                "qa_kind": "landsat",
                "band_map": {"SR_B1": "blue", "SR_B2": "green", "SR_B3": "red", "SR_B4": "nir", "SR_B5": "swir1", "SR_B7": "swir2"},
            },
            {
                "source_id": "gee_landsat_c2_l2",
                "collection": "LANDSAT/LE07/C02/T1_L2",
                "sensor": "Landsat",
                "scale": 30,
                "qa_kind": "landsat",
                "band_map": {"SR_B1": "blue", "SR_B2": "green", "SR_B3": "red", "SR_B4": "nir", "SR_B5": "swir1", "SR_B7": "swir2"},
            },
            {
                "source_id": "gee_landsat_c2_l2",
                "collection": "LANDSAT/LC08/C02/T1_L2",
                "sensor": "Landsat",
                "scale": 30,
                "qa_kind": "landsat",
                "band_map": {"SR_B2": "blue", "SR_B3": "green", "SR_B4": "red", "SR_B5": "nir", "SR_B6": "swir1", "SR_B7": "swir2"},
            },
            {
                "source_id": "gee_landsat_c2_l2",
                "collection": "LANDSAT/LC09/C02/T1_L2",
                "sensor": "Landsat",
                "scale": 30,
                "qa_kind": "landsat",
                "band_map": {"SR_B2": "blue", "SR_B3": "green", "SR_B4": "red", "SR_B5": "nir", "SR_B6": "swir1", "SR_B7": "swir2"},
            },
        ]
    raise ValueError(f"Unsupported optical GEE source: {source}")


def _source_id_for_gee_source(source: str) -> str:
    return {
        "hls": "gee_hls_s30_l30",
        "sentinel2": "gee_sentinel2_sr_harmonized",
        "landsat_c2": "gee_landsat_c2_l2",
        "era5_land": "gee_era5_land",
        "modis_snow": "gee_modis_mod10a1",
        "smap": "gee_smap_context_optional",
    }[source]


def _write_extraction_summary(source: str, rows: list[dict[str, Any]], frame: pd.DataFrame) -> None:
    table = pd.DataFrame(rows)
    file_stem = {
        "hls": "gee_hls_extraction_summary",
        "sentinel2": "gee_sentinel2_extraction_summary",
        "landsat_c2": "gee_landsat_c2_extraction_summary",
        "era5_land": "gee_era5_land_extraction_summary",
        "modis_snow": "gee_modis_snow_extraction_summary",
        "smap": "gee_smap_extraction_summary",
    }[source]
    table.to_csv(TABLE_DIR / f"{file_stem}.csv", index=False, encoding="utf-8")
    lines = [
        f"# {file_stem.replace('_', ' ').title()}",
        "",
        f"Generated: {utc_now()}",
        "",
        "No DOC model was trained. No DOC prediction or flux product was generated.",
        "",
        "## Chunk Summary",
        table.to_markdown(index=False) if not table.empty else "_No rows._",
        "",
        "## Canonical Rows",
        frame.groupby(["river", "source_id"], dropna=False).size().reset_index(name="rows").to_markdown(index=False) if not frame.empty and "river" in frame.columns else "_No regenerated rows._",
    ]
    (REPORT_DIR / f"{file_stem.replace('_summary', '_report')}.md").write_text("\n".join(lines), encoding="utf-8")


def _era5_feature(ee: Any, image: Any, geom: Any, river: str, roi_set: str) -> Any:
    date = ee.Date(image.get("system:time_start"))
    temp_c = image.select("temperature_2m").subtract(273.15).rename("temperature_2m_C")
    pdd = temp_c.max(0).rename("positive_degree_day_Cday")
    bands = ee.Image.cat(
        [
            temp_c,
            image.select("total_precipitation_sum").rename("precipitation_m"),
            image.select("snow_depth").rename("snow_depth_m"),
            image.select("snowmelt_sum").rename("snowmelt_m"),
            image.select("surface_runoff_sum").rename("surface_runoff_m"),
            image.select("sub_surface_runoff_sum").rename("subsurface_runoff_m"),
            image.select("runoff_sum").rename("total_runoff_m"),
            pdd,
        ]
    )
    stats = bands.reduceRegion(ee.Reducer.mean(), geom, 10000, maxPixels=1e9, bestEffort=True)
    props = ee.Dictionary(
        {
            "river": river,
            "date": date.format("YYYY-MM-dd"),
            "aggregation_geometry": "final_primary_roi",
            "aggregation_geometry_id": f"{river}_{roi_set}",
            "source_id": "gee_era5_land",
            "quality_flag": REGENERATED_QUALITY,
            "snapshot_path": "",
            "original_relative_path": "",
            "sha256": "",
            "notes": "Regenerated from Earth Engine ECMWF/ERA5_LAND/DAILY_AGGR as daily equivalent to ERA5-Land hourly; final_primary ROI aggregation, not basin-level.",
        }
    )
    return ee.Feature(
        None,
        ee.Dictionary(stats).combine(props, overwrite=True),
    )


def extract_era5(rivers: str, years: str, roi_set: str) -> pd.DataFrame:
    init = _import_ee()
    source_id = "gee_era5_land"
    if not init.ok:
        for river in _selected_rivers(rivers):
            for year in _parse_years(years):
                _manifest_failure(source_id, "era5_land", river, year, init.error)
        return pd.DataFrame()
    ee = init.ee
    frames = []
    summary = []
    for river in _selected_rivers(rivers):
        geom = _ee_geometry(ee, river, roi_set)
        for year in _parse_years(years):
            try:
                collection = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(f"{year}-01-01", f"{year + 1}-01-01").filterBounds(geom)
                rows = _feature_collection_rows(collection.map(lambda image: _era5_feature(ee, image, geom, river, roi_set)))
                frame = ensure_columns(pd.DataFrame(rows), HYDRO_SCHEMA)
                if not frame.empty:
                    chunk = _write_chunk(frame, source_id, "era5_land", river, year)
                    frame["original_relative_path"] = relpath(chunk)
                    frame["sha256"] = sha256_file(chunk)
                    frames.append(frame)
                summary.append({"source_id": source_id, "river": river, "year": year, "rows": len(frame), "status": "downloaded" if not frame.empty else "empty", "failure_reason": ""})
            except Exception as exc:
                _manifest_failure(source_id, "era5_land", river, year, f"{type(exc).__name__}: {exc}")
                summary.append({"source_id": source_id, "river": river, "year": year, "rows": 0, "status": "failed", "failure_reason": f"{type(exc).__name__}: {exc}"})
    regenerated = pd.concat(frames, ignore_index=True) if frames else ensure_columns(pd.DataFrame(), HYDRO_SCHEMA)
    _append_hydro(regenerated)
    _write_extraction_summary("era5_land", summary, regenerated)
    return regenerated


def _modis_feature(ee: Any, image: Any, geom: Any, river: str, roi_set: str) -> Any:
    date = ee.Date(image.get("system:time_start"))
    snow = image.select("NDSI_Snow_Cover")
    valid = snow.lte(100)
    snow_masked = snow.updateMask(valid)
    mean = snow_masked.reduceRegion(ee.Reducer.mean(), geom, 500, maxPixels=1e9, bestEffort=True).get("NDSI_Snow_Cover")
    count = snow_masked.reduceRegion(ee.Reducer.count(), geom, 500, maxPixels=1e9, bestEffort=True).get("NDSI_Snow_Cover")
    fraction = ee.Algorithms.If(mean, ee.Number(mean).divide(100), None)
    return ee.Feature(
        None,
        {
            "river": river,
            "date": date.format("YYYY-MM-dd"),
            "mean_ndsi_snow_cover": mean,
            "valid_modis_pixels": count,
            "snow_cover_fraction": fraction,
            "source_id": "gee_modis_mod10a1",
            "quality_flag": REGENERATED_QUALITY,
            "roi_set": roi_set,
            "notes": "MODIS NDSI_Snow_Cover masked where provider values >100.",
        },
    )


def extract_modis(rivers: str, years: str, roi_set: str) -> pd.DataFrame:
    init = _import_ee()
    source_id = "gee_modis_mod10a1"
    if not init.ok:
        return pd.DataFrame()
    ee = init.ee
    frames = []
    qc_frames = []
    summary = []
    for river in _selected_rivers(rivers):
        geom = _ee_geometry(ee, river, roi_set)
        for year in _parse_years(years):
            try:
                collection = ee.ImageCollection("MODIS/061/MOD10A1").filterDate(f"{year}-01-01", f"{year + 1}-01-01").filterBounds(geom)
                rows = _feature_collection_rows(collection.map(lambda image: _modis_feature(ee, image, geom, river, roi_set)))
                qc = pd.DataFrame(rows)
                qc_frames.append(qc)
                hydro = pd.DataFrame(
                    {
                        "river": qc.get("river", pd.Series(dtype=str)),
                        "date": qc.get("date", pd.Series(dtype=str)),
                        "aggregation_geometry": "final_primary_roi",
                        "aggregation_geometry_id": f"{river}_{roi_set}",
                        "snow_cover_fraction": qc.get("snow_cover_fraction", pd.Series(dtype=float)),
                        "source_id": source_id,
                        "quality_flag": REGENERATED_QUALITY,
                        "snapshot_path": "",
                        "original_relative_path": "",
                        "sha256": "",
                        "notes": "Regenerated MODIS snow cover from GEE; snow_depletion_rate_7d computed after merge.",
                    }
                )
                hydro = ensure_columns(hydro, HYDRO_SCHEMA)
                if not hydro.empty:
                    chunk = _write_chunk(hydro, source_id, "modis_snow", river, year)
                    hydro["original_relative_path"] = relpath(chunk)
                    hydro["sha256"] = sha256_file(chunk)
                    frames.append(hydro)
                summary.append({"source_id": source_id, "river": river, "year": year, "rows": len(hydro), "status": "downloaded" if not hydro.empty else "empty", "failure_reason": ""})
            except Exception as exc:
                _manifest_failure(source_id, "modis_snow", river, year, f"{type(exc).__name__}: {exc}")
                summary.append({"source_id": source_id, "river": river, "year": year, "rows": 0, "status": "failed", "failure_reason": f"{type(exc).__name__}: {exc}"})
    regenerated = pd.concat(frames, ignore_index=True) if frames else ensure_columns(pd.DataFrame(), HYDRO_SCHEMA)
    if not regenerated.empty:
        regenerated["date_dt"] = pd.to_datetime(regenerated["date"], errors="coerce")
        regenerated = regenerated.sort_values(["river", "date_dt"])
        regenerated["snow_depletion_rate_7d"] = regenerated.groupby("river")["snow_cover_fraction"].transform(lambda s: pd.to_numeric(s, errors="coerce").diff(7))
        regenerated = regenerated.drop(columns=["date_dt"])
    qc_all = pd.concat(qc_frames, ignore_index=True) if qc_frames else pd.DataFrame()
    qc_all.to_csv(TABLE_DIR / "modis_snow_qc_sidecar.csv", index=False, encoding="utf-8")
    _append_hydro(regenerated)
    _write_extraction_summary("modis_snow", summary, regenerated)
    return regenerated


def _append_hydro(regenerated: pd.DataFrame) -> pd.DataFrame:
    existing_path = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    existing = ensure_columns(read_table_if_exists(HYDRO_SCHEMA), HYDRO_SCHEMA)
    if regenerated.empty:
        return existing
    regen_sources = set(regenerated["source_id"].astype(str))
    non_same = existing[~existing["source_id"].astype(str).isin(regen_sources)]
    combined = pd.concat([non_same, regenerated], ignore_index=True)
    combined = combined.drop_duplicates(["river", "date", "source_id", "aggregation_geometry_id"], keep="last")
    write_table(ensure_columns(combined, HYDRO_SCHEMA), HYDRO_SCHEMA, existing_path)
    return ensure_columns(combined, HYDRO_SCHEMA)


def extract_smap(rivers: str, years: str, roi_set: str) -> pd.DataFrame:
    # Optional source: keep implementation conservative. It records an optional failure unless extended later.
    source_id = "gee_smap_context_optional"
    for river in _selected_rivers(rivers):
        for year in _parse_years(years):
            _manifest_failure(source_id, "smap", river, year, "SMAP optional extraction deferred/failed_optional; not a full-training blocker.")
    pd.DataFrame(columns=["source_id", "river", "year", "rows", "status", "failure_reason"]).to_csv(TABLE_DIR / "gee_smap_extraction_summary.csv", index=False, encoding="utf-8")
    (REPORT_DIR / "gee_smap_extraction_report.md").write_text("# GEE SMAP Extraction Report\n\nSMAP optional extraction is marked failed_optional/deferred and is not a full-training blocker.\n", encoding="utf-8")
    return ensure_columns(pd.DataFrame(), AUX_SCHEMA)


def run_gee_extraction(source: str, rivers: str, years: str, roi_set: str) -> pd.DataFrame:
    source = source.lower()
    if source == "hls":
        return extract_optical_source("hls", rivers, years or "2016-2025", roi_set)
    if source == "sentinel2":
        return extract_optical_source("sentinel2", rivers, years or "2017-2025", roi_set)
    if source == "landsat_c2":
        return extract_optical_source("landsat_c2", rivers, years or "2003-2025", roi_set)
    if source == "era5_land":
        return extract_era5(rivers, years or "2000-2025", roi_set)
    if source == "modis_snow":
        return extract_modis(rivers, years or "2000-2025", roi_set)
    if source == "smap":
        return extract_smap(rivers, years or "2015-2025", roi_set)
    raise ValueError(f"Unsupported GEE source: {source}")


def run_all_gee_extractions(roi_set: str = "final_primary") -> None:
    run_gee_extraction("hls", "all", "2016-2025", roi_set)
    run_gee_extraction("sentinel2", "all", "2017-2025", roi_set)
    run_gee_extraction("landsat_c2", "all", "2003-2025", roi_set)
    run_gee_extraction("era5_land", "all", "2000-2025", roi_set)
    run_gee_extraction("modis_snow", "all", "2000-2025", roi_set)
    run_gee_extraction("smap", "all", "2015-2025", roi_set)
    generate_gee_regeneration_comparison()


def generate_gee_regeneration_comparison() -> tuple[pd.DataFrame, pd.DataFrame]:
    hydro = read_table_if_exists(HYDRO_SCHEMA)
    optical = read_table_if_exists(OPTICAL_SCHEMA)
    hydro_rows = []
    if not hydro.empty:
        legacy = hydro[hydro["source_id"].astype(str) == LEGACY_SOURCE]
        regen = hydro[hydro["quality_flag"].astype(str) == REGENERATED_QUALITY]
        for variable in ["temperature_2m_C", "snowmelt_m", "surface_runoff_m", "snow_cover_fraction"]:
            merged = legacy[["river", "date", variable]].merge(regen[["river", "date", variable]], on=["river", "date"], how="outer", suffixes=("_legacy", "_regenerated"))
            for _, row in merged.iterrows():
                lv = pd.to_numeric(pd.Series([row.get(f"{variable}_legacy")]), errors="coerce").iloc[0]
                rv = pd.to_numeric(pd.Series([row.get(f"{variable}_regenerated")]), errors="coerce").iloc[0]
                if pd.notna(lv) and pd.notna(rv):
                    status = "regenerated_preferred" if abs(float(rv) - float(lv)) <= max(abs(float(lv)) * 10, 1000) else "conflict_requires_audit"
                    diff = float(rv) - float(lv)
                    rel = diff / float(lv) if lv else pd.NA
                elif pd.isna(rv) and pd.notna(lv):
                    status = "regenerated_missing_legacy_available"
                    diff = pd.NA
                    rel = pd.NA
                elif pd.notna(rv) and pd.isna(lv):
                    status = "legacy_missing_regenerated_available"
                    diff = pd.NA
                    rel = pd.NA
                else:
                    status = "both_missing"
                    diff = pd.NA
                    rel = pd.NA
                hydro_rows.append({"river": row["river"], "date": row["date"], "variable": variable, "legacy_value": lv, "regenerated_value": rv, "difference": diff, "relative_difference": rel, "status": status})
    hydro_compare = pd.DataFrame(hydro_rows)
    hydro_compare.to_csv(TABLE_DIR / "gee_legacy_vs_regenerated_hydroclimate_compare.csv", index=False, encoding="utf-8")

    optical_rows = []
    if not optical.empty:
        optical["date"] = pd.to_datetime(optical["date"], errors="coerce").dt.date.astype(str)
        grouped = optical.groupby(["river", "date", "sensor"], dropna=False)
        for (river, date, sensor), group in grouped:
            legacy_rows = group[group["source_id"].astype(str) == LEGACY_SOURCE]
            regen_rows = group[group["quality_flag"].astype(str) == REGENERATED_QUALITY]
            status = "regenerated_preferred" if not regen_rows.empty else ("regenerated_missing_legacy_available" if not legacy_rows.empty else "legacy_missing_regenerated_available")
            optical_rows.append(
                {
                    "river": river,
                    "date": date,
                    "sensor": sensor,
                    "legacy_rows": len(legacy_rows),
                    "regenerated_rows": len(regen_rows),
                    "valid_water_pixel_change": pd.to_numeric(regen_rows.get("n_valid_water_pixels", pd.Series(dtype=float)), errors="coerce").mean() - pd.to_numeric(legacy_rows.get("n_valid_water_pixels", pd.Series(dtype=float)), errors="coerce").mean() if not legacy_rows.empty and not regen_rows.empty else pd.NA,
                    "band_median_difference_if_comparable": "",
                    "status": status,
                }
            )
    optical_compare = pd.DataFrame(optical_rows)
    optical_compare.to_csv(TABLE_DIR / "gee_legacy_vs_regenerated_optical_compare.csv", index=False, encoding="utf-8")
    lines = [
        "# GEE Regeneration Comparison Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "No DOC model was trained. No DOC prediction or flux product was generated.",
        "",
        "## Hydroclimate Status Counts",
        hydro_compare.groupby("status").size().reset_index(name="rows").to_markdown(index=False) if not hydro_compare.empty else "_No hydro comparison rows._",
        "",
        "## Optical Status Counts",
        optical_compare.groupby("status").size().reset_index(name="rows").to_markdown(index=False) if not optical_compare.empty else "_No optical comparison rows._",
    ]
    (REPORT_DIR / "gee_regeneration_comparison_report.md").write_text("\n".join(lines), encoding="utf-8")
    return hydro_compare, optical_compare
