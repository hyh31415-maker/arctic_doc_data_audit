from __future__ import annotations

import json
import math
import re
import shutil
import zipfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import pandas as pd
import requests
import yaml

from .manifest import append_manifest, manifest_failure, manifest_for_file, read_manifest, sha256_file, utc_now, write_manifest
from .normalize import load_rivers, station_for_river
from .paths import CONFIG_DIR, PROCESSED_DIR, RAW_EXTERNAL_DIR, REPORT_DIR, TABLE_DIR, ensure_project_dirs, path, relpath
from .schemas import ensure_columns, read_table_if_exists, write_table


NO_MODEL_TEXT = "No DOC model was trained. No DOC prediction or flux product was generated."
HYDROSHEDS_LICENSE = "HydroSHEDS/HydroBASINS license terms; HydroATLAS CC-BY 4.0 where applicable. See official product pages and technical documentation."

REGION_CODES = {
    "Africa": "af",
    "Arctic": "ar",
    "Asia": "as",
    "Australia": "au",
    "Europe": "eu",
    "Greenland": "gr",
    "North America": "na",
    "South America": "sa",
    "Siberia": "si",
}

HYDRORIVERS_REGIONS = {
    "Global": "",
    "Africa": "af",
    "Arctic": "ar",
    "Asia": "as",
    "Australasia": "au",
    "Europe and Middle East": "eu",
    "Greenland": "gr",
    "North and Central America": "na",
    "South America": "sa",
    "Siberia": "si",
}

RIVER_REGION_HINTS = {
    "Ob": ["Siberia", "Asia", "Arctic"],
    "Yenisey": ["Siberia", "Asia", "Arctic"],
    "Lena": ["Siberia", "Asia", "Arctic"],
    "Kolyma": ["Siberia", "Asia", "Arctic"],
    "Yukon": ["North America", "North and Central America", "Arctic"],
    "Mackenzie": ["North America", "North and Central America", "Arctic"],
}

KEY_COLUMNS = {
    "id": ["HYBAS_ID", "HYRIV_ID", "BAS_ID", "basin_id", "OBJECTID"],
    "area": ["SUB_AREA", "UP_AREA", "AREA_SQKM", "area_km2", "Shape_Area"],
    "pfaf": ["PFAF_ID", "PFAF", "pfaf_id"],
    "next_down": ["NEXT_DOWN", "NEXT_DOWNID", "NextDownID"],
    "river": ["HYRIV_ID", "MAIN_RIV", "ORD_STRA", "DIS_AV_CMS", "LENGTH_KM", "DIST_DN_KM", "HYBAS_ID", "BAS_ID"],
}


@dataclass(frozen=True)
class DownloadProduct:
    source_id: str
    dataset_family: str
    product_name: str
    region: str
    file_format: str
    level: str
    official_page: str
    url_pattern: str
    enabled: bool = True
    optional: bool = False
    file_name: str = ""


def _write_csv(frame: pd.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")
    return destination


def _read_csv(destination: Path) -> pd.DataFrame:
    if not destination.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(destination, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def _md_table(frame: pd.DataFrame, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def _load_config() -> dict[str, Any]:
    config_path = CONFIG_DIR / "hydrosheds_full.yaml"
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _resolve_project_path(value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return path(candidate)


def _download_root(config: dict[str, Any] | None = None) -> Path:
    config = config or _load_config()
    return _resolve_project_path(config.get("download_root", RAW_EXTERNAL_DIR / "hydrosheds_full"))


def _unpack_root(config: dict[str, Any] | None = None) -> Path:
    config = config or _load_config()
    return _resolve_project_path(config.get("unpack_root", RAW_EXTERNAL_DIR / "hydrosheds_full" / "unpacked"))


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_").lower() or "product"


def _version_from_name(value: str) -> str:
    for pattern in (r"_v([0-9][A-Za-z0-9_.-]*)", r"v([0-9]+(?:_[0-9]+)?)"):
        match = re.search(pattern, value)
        if match:
            return match.group(1).strip("._-")
    return ""


def _disk_free_gb(target: Path) -> float | None:
    try:
        target.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(target)
        return usage.free / 1024**3
    except Exception:
        return None


def _url_basename(url: str, fallback: str) -> str:
    name = Path(unquote(urlparse(url).path)).name
    if not name or "." not in name:
        name = fallback
    return name


def _discover_urls(page_url: str) -> list[str]:
    try:
        response = requests.get(page_url, timeout=45)
        response.raise_for_status()
    except Exception:
        return []
    urls = re.findall(r"https?://[^\"'<> )]+", response.text)
    return sorted({url.rstrip(".,);") for url in urls if "hydrosheds" in url.lower() or "figshare.com" in url.lower()})


def _manual_urls(config: dict[str, Any]) -> dict[str, str]:
    raw = config.get("manual_download_urls") or {}
    return {str(key): str(value) for key, value in raw.items()}


def _head_size(url: str) -> int | str:
    try:
        response = requests.head(url, timeout=30, allow_redirects=True)
        if response.ok and response.headers.get("content-length"):
            return int(response.headers["content-length"])
    except Exception:
        pass
    try:
        response = requests.get(url, timeout=30, stream=True, allow_redirects=True, headers={"Range": "bytes=0-0"})
        content_range = response.headers.get("content-range", "")
        response.close()
        match = re.search(r"/(\d+)$", content_range)
        if match:
            return int(match.group(1))
        if response.headers.get("content-length") and response.status_code == 200:
            return int(response.headers["content-length"])
    except Exception:
        pass
    return ""


def _products(config: dict[str, Any], include_disabled: bool = False) -> list[DownloadProduct]:
    pages = config.get("official_pages") or {}
    enabled = config.get("download_products") or {}
    products: list[DownloadProduct] = []
    for region, code in REGION_CODES.items():
        products.append(
            DownloadProduct(
                source_id="hydrobasins_standard_full",
                dataset_family="HydroBASINS standard",
                product_name=f"HydroBASINS standard {region} all levels 1-12",
                region=region,
                file_format="shapefile_zip",
                level="01-12",
                official_page=pages.get("hydrobasins", "https://www.hydrosheds.org/products/hydrobasins"),
                url_pattern=f"hydrobasins/standard/hybas_{code}_lev01-12_v1c.zip",
                enabled=bool(enabled.get("hydrobasins_standard_full", True)),
            )
        )
        products.append(
            DownloadProduct(
                source_id="hydrobasins_custom_lakes_full",
                dataset_family="HydroBASINS customized with lakes",
                product_name=f"HydroBASINS customized with lakes {region} all levels 1-12",
                region=region,
                file_format="shapefile_zip",
                level="01-12",
                official_page=pages.get("hydrobasins", "https://www.hydrosheds.org/products/hydrobasins"),
                url_pattern=f"hydrobasins/customized_with_lakes/hybas_lake_{code}_lev01-12_v1c.zip",
                enabled=bool(enabled.get("hydrobasins_custom_lakes_full", True)),
                optional=True,
            )
        )
    products.append(
        DownloadProduct(
            source_id="hydrobasins_pour_points_full",
            dataset_family="HydroBASINS pour points",
            product_name="HydroBASINS pour points levels 1-12 combined",
            region="Global",
            file_format="shapefile_zip",
            level="01-12",
            official_page=pages.get("hydrobasins", "https://www.hydrosheds.org/products/hydrobasins"),
            url_pattern="hydrobasins/pour_point/hybas_pour_lev01-12_v1_shp.zip",
            enabled=bool(enabled.get("hydrobasins_pour_points_full", True)),
            optional=True,
        )
    )
    products.append(
        DownloadProduct(
            source_id="hydrorivers_global",
            dataset_family="HydroRIVERS",
            product_name="HydroRIVERS global geodatabase",
            region="Global",
            file_format="geodatabase_zip",
            level="",
            official_page=pages.get("hydrorivers", "https://www.hydrosheds.org/products/hydrorivers"),
            url_pattern="HydroRIVERS/HydroRIVERS_v10.gdb.zip",
            enabled=bool(enabled.get("hydrorivers_global", True)),
        )
    )
    for region, code in HYDRORIVERS_REGIONS.items():
        if region == "Global":
            continue
        products.append(
            DownloadProduct(
                source_id="hydrorivers_global",
                dataset_family="HydroRIVERS continental fallback",
                product_name=f"HydroRIVERS {region} geodatabase fallback",
                region=region,
                file_format="geodatabase_zip",
                level="",
                official_page=pages.get("hydrorivers", "https://www.hydrosheds.org/products/hydrorivers"),
                url_pattern=f"HydroRIVERS/HydroRIVERS_v10_{code}.gdb.zip",
                enabled=bool(enabled.get("hydrorivers_continental_fallback", True)),
                optional=True,
            )
        )
    products.append(
        DownloadProduct(
            source_id="hydrorivers_global_fallback_shapefile",
            dataset_family="HydroRIVERS shapefile fallback",
            product_name="HydroRIVERS global shapefile fallback",
            region="Global",
            file_format="shapefile_zip",
            level="",
            official_page=pages.get("hydrorivers", "https://www.hydrosheds.org/products/hydrorivers"),
            url_pattern="HydroRIVERS/HydroRIVERS_v10_shp.zip",
            enabled=bool(enabled.get("shapefile_fallbacks", False)),
            optional=True,
        )
    )
    atlas_page = pages.get("hydroatlas", "https://www.hydrosheds.org/hydroatlas")
    products.extend(
        [
            DownloadProduct("basinatlas_global_gdb", "HydroATLAS BasinATLAS", "Global BasinATLAS geodatabase", "Global", "geodatabase_zip", "", atlas_page, "https://ndownloader.figshare.com/files/20082137", bool(enabled.get("basinatlas_global_gdb", True)), file_name="BasinATLAS_Data_v10.gdb.zip"),
            DownloadProduct("riveratlas_global_gdb", "HydroATLAS RiverATLAS", "Global RiverATLAS geodatabase", "Global", "geodatabase_zip", "", atlas_page, "https://ndownloader.figshare.com/files/20087321", bool(enabled.get("riveratlas_global_gdb", True)), file_name="RiverATLAS_Data_v10.gdb.zip"),
            DownloadProduct("lakeatlas_global_gdb", "HydroATLAS LakeATLAS", "Global LakeATLAS geodatabase", "Global", "geodatabase_zip", "", atlas_page, "https://ndownloader.figshare.com/files/35959544", bool(enabled.get("lakeatlas_global_gdb", True)), optional=True, file_name="LakeATLAS_Data_v10.gdb.zip"),
            DownloadProduct("basinatlas_global_shp_fallback", "HydroATLAS BasinATLAS shapefile fallback", "Global BasinATLAS shapefile fallback", "Global", "shapefile_zip", "", atlas_page, "https://ndownloader.figshare.com/files/20087237", bool(enabled.get("shapefile_fallbacks", False)), optional=True, file_name="BasinATLAS_Data_v10_shp.zip"),
            DownloadProduct("riveratlas_global_shp_fallback", "HydroATLAS RiverATLAS shapefile fallback", "Global RiverATLAS shapefile fallback", "Global", "shapefile_zip", "", atlas_page, "https://ndownloader.figshare.com/files/20087486", bool(enabled.get("shapefile_fallbacks", False)), optional=True, file_name="RiverATLAS_Data_v10_shp.zip"),
            DownloadProduct("lakeatlas_global_shp_fallback", "HydroATLAS LakeATLAS shapefile fallback", "Global LakeATLAS shapefile fallback", "Global", "shapefile_zip", "", atlas_page, "https://ndownloader.figshare.com/files/35959547", bool(enabled.get("shapefile_fallbacks", False)), optional=True, file_name="LakeATLAS_Data_v10_shp.zip"),
            DownloadProduct("hydroatlas_technical_documentation", "HydroATLAS documentation", "HydroATLAS technical documentation v10.1", "Global", "pdf", "", atlas_page, "https://data.hydrosheds.org/file/technical-documentation/HydroATLAS_TechDoc_v10_1.pdf", bool(enabled.get("hydroatlas_documentation", True)), optional=True, file_name="HydroATLAS_TechDoc_v10_1.pdf"),
            DownloadProduct("basinatlas_catalog_pdf", "HydroATLAS documentation", "BasinATLAS Catalog v10", "Global", "pdf", "", atlas_page, "https://data.hydrosheds.org/file/technical-documentation/BasinATLAS_Catalog_v10.pdf", bool(enabled.get("hydroatlas_documentation", True)), optional=True, file_name="BasinATLAS_Catalog_v10.pdf"),
            DownloadProduct("riveratlas_catalog_pdf", "HydroATLAS documentation", "RiverATLAS Catalog v10", "Global", "pdf", "", atlas_page, "https://data.hydrosheds.org/file/technical-documentation/RiverATLAS_Catalog_v10.pdf", bool(enabled.get("hydroatlas_documentation", True)), optional=True, file_name="RiverATLAS_Catalog_v10.pdf"),
            DownloadProduct("lakeatlas_catalog_pdf", "HydroATLAS documentation", "LakeATLAS Catalog v10", "Global", "pdf", "", atlas_page, "https://data.hydrosheds.org/file/technical-documentation/LakeATLAS_Catalog_v10.pdf", bool(enabled.get("hydroatlas_documentation", True)), optional=True, file_name="LakeATLAS_Catalog_v10.pdf"),
        ]
    )
    if include_disabled:
        return products
    return [product for product in products if product.enabled]


def _resolve_download_url(product: DownloadProduct, discovered: dict[str, list[str]], manual: dict[str, str]) -> str:
    manual_key = product.source_id + ":" + _safe_name(product.product_name)
    if manual.get(manual_key):
        return manual[manual_key]
    if manual.get(product.source_id):
        return manual[product.source_id]
    candidates = discovered.get(product.official_page, [])
    pattern = product.url_pattern.lower()
    for url in candidates:
        if pattern in url.lower():
            return url
    if product.url_pattern.startswith("http"):
        return product.url_pattern
    if product.url_pattern:
        return f"https://data.hydrosheds.org/file/{product.url_pattern.lstrip('/')}"
    return ""


def _safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        root = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(destination)


def _download_file(url: str, destination: Path, expected_size: int | str = "") -> tuple[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    resume_from = tmp.stat().st_size if tmp.exists() else 0
    expected = int(expected_size) if str(expected_size).isdigit() else None
    if expected is not None and resume_from >= expected:
        tmp.replace(destination)
        return "downloaded", ""
    headers = {"Range": f"bytes={resume_from}-"} if resume_from else {}
    try:
        with requests.get(url, stream=True, timeout=60, allow_redirects=True, headers=headers) as response:
            response.raise_for_status()
            mode = "ab" if resume_from and response.status_code == 206 else "wb"
            with tmp.open(mode) as handle:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        handle.write(block)
        if expected is not None and tmp.stat().st_size != expected:
            return "partial", f"Downloaded {tmp.stat().st_size} bytes; expected {expected} bytes. Resume by rerunning download-hydrosheds-full."
        tmp.replace(destination)
        return "downloaded", ""
    except Exception as exc:
        return "failed", str(exc)


def _should_unpack(product: DownloadProduct, config: dict[str, Any]) -> bool:
    policy = config.get("unpack_policy") or {}
    if product.file_format == "pdf":
        return bool(policy.get("documentation", False))
    if product.source_id.startswith("hydrobasins"):
        return bool(policy.get("hydrobasins", True))
    if product.source_id.startswith("hydrorivers"):
        return bool(policy.get("hydrorivers", True))
    if product.source_id in {"basinatlas_global_gdb", "riveratlas_global_gdb", "lakeatlas_global_gdb"}:
        return bool(policy.get("hydroatlas_gdb", True))
    if product.source_id.endswith("_shp_fallback"):
        return bool(policy.get("hydroatlas_shapefile_fallbacks", False))
    return zipfile.is_zipfile(Path(product.file_name))


def _mark_superseded_manifest_failures(success_source_ids: set[str]) -> None:
    if not success_source_ids:
        return
    manifest = read_manifest()
    if manifest.empty:
        return
    mask = manifest["source_id"].astype(str).isin(success_source_ids) & manifest["download_status"].astype(str).eq("failed")
    if not mask.any():
        return
    manifest.loc[mask, "download_status"] = "superseded_failed"
    manifest.loc[mask, "failure_reason"] = manifest.loc[mask, "failure_reason"].astype(str) + " | Superseded by later successful stable ndownloader/data.hydrosheds download."
    write_manifest(manifest)


def download_hydrosheds_full(all_products: bool = False) -> pd.DataFrame:
    """Download or explicitly record full HydroSHEDS/HydroATLAS acquisition status."""
    ensure_project_dirs()
    config = _load_config()
    download_root = _download_root(config)
    unpack_root = _unpack_root(config)
    download_root.mkdir(parents=True, exist_ok=True)
    unpack_root.mkdir(parents=True, exist_ok=True)

    disk_policy = config.get("disk_safety") or {}
    free_before = _disk_free_gb(download_root)
    min_free = float(disk_policy.get("min_free_space_gb", 80))
    allow_unknown = bool(disk_policy.get("allow_continue_if_space_unknown", False))
    disk_blocked = free_before is None and not allow_unknown
    if free_before is not None and free_before < min_free:
        disk_blocked = True

    products = _products(config, include_disabled=True)
    pages = sorted({product.official_page for product in products})
    discovered = {page: _discover_urls(page) for page in pages}
    manual = _manual_urls(config)

    rows: list[dict[str, Any]] = []
    successful_source_ids: set[str] = set()
    for product in products:
        url = _resolve_download_url(product, discovered, manual)
        file_name = product.file_name or (_url_basename(url, _safe_name(product.product_name) + ".zip") if url else _safe_name(product.product_name) + ".zip")
        local_zip = download_root / product.source_id / file_name
        unpacked = unpack_root / product.source_id / Path(file_name).stem
        size = ""
        expected_size = ""
        size_check_status = ""
        status = "pending"
        failure = ""
        resolved = ""
        sha = ""
        if not product.enabled:
            status = "disabled_by_config"
            failure = "Product disabled in configs/hydrosheds_full.yaml."
        elif not url:
            status = "manual_required"
            failure = "Official page parsing did not expose a download URL and no manual URL is configured."
            append_manifest(
                manifest_failure(
                    source_id=product.source_id,
                    source_url=product.official_page,
                    failure_reason=failure,
                    license_or_citation=HYDROSHEDS_LICENSE,
                    local_path=local_zip,
                )
            )
        elif disk_blocked:
            status = "failed_disk_safety"
            failure = f"Free disk space is {free_before if free_before is not None else 'unknown'} GB; policy requires at least {min_free} GB."
            append_manifest(
                manifest_failure(
                    source_id=product.source_id,
                    source_url=product.official_page,
                    download_url=url,
                    resolved_url=url,
                    failure_reason=failure,
                    license_or_citation=HYDROSHEDS_LICENSE,
                    local_path=local_zip,
                )
            )
        else:
            if local_zip.exists():
                status = "already_present"
                sha = sha256_file(local_zip)
                size = local_zip.stat().st_size
                expected_size = _head_size(url)
            else:
                expected_size = _head_size(url)
                size = expected_size
                status, failure = _download_file(url, local_zip, expected_size=expected_size)
                if status == "downloaded":
                    sha = sha256_file(local_zip)
                    size = local_zip.stat().st_size
            if str(expected_size).isdigit() and local_zip.exists():
                size_check_status = "ok" if int(local_zip.stat().st_size) == int(expected_size) else "size_mismatch"
                if size_check_status == "size_mismatch":
                    failure = (failure + " " if failure else "") + f"Local size {local_zip.stat().st_size} differs from expected {expected_size}."
            if status in {"downloaded", "already_present"}:
                resolved = url
                append_manifest(
                    manifest_for_file(
                        source_id=product.source_id,
                        source_url=product.official_page,
                        download_url=url,
                        resolved_url=resolved,
                        local_path=local_zip,
                        version_detected=_version_from_name(file_name),
                        license_or_citation=HYDROSHEDS_LICENSE,
                        status="downloaded" if status == "downloaded" else "already_present",
                    )
                )
                successful_source_ids.add(product.source_id)
                if _should_unpack(product, config):
                    try:
                        if unpacked.exists() and any(unpacked.rglob("*")):
                            unpack_status = "already_unpacked"
                        elif zipfile.is_zipfile(local_zip):
                            _safe_extract(local_zip, unpacked)
                            unpack_status = "unpacked"
                        else:
                            unpack_status = "not_zip_or_unreadable"
                            failure = "Downloaded file is not a readable zip archive."
                    except Exception as exc:
                        unpack_status = "unpack_failed"
                        failure = str(exc)
                        status = "partial"
                    if unpack_status in {"unpacked", "already_unpacked"}:
                        status = status if status == "already_present" else "downloaded"
                    else:
                        status = status if status == "partial" else unpack_status
                else:
                    unpack_status = "not_unpacked_by_policy"
            else:
                append_manifest(
                    manifest_failure(
                        source_id=product.source_id,
                        source_url=product.official_page,
                        download_url=url,
                        resolved_url=url,
                        failure_reason=failure,
                        license_or_citation=HYDROSHEDS_LICENSE,
                        local_path=local_zip,
                    )
                )
        if not sha and local_zip.exists():
            sha = sha256_file(local_zip)
        if not size and local_zip.exists():
            size = local_zip.stat().st_size
        rows.append(
            {
                "source_id": product.source_id,
                "dataset_family": product.dataset_family,
                "product_name": product.product_name,
                "region": product.region,
                "format": product.file_format,
                "level": product.level,
                "download_url": url,
                "resolved_url": resolved or url,
                "local_zip_path": relpath(local_zip),
                "unpacked_path": relpath(unpacked) if unpacked.exists() else "",
                "expected_file_size_bytes": expected_size,
                "file_size_bytes": size,
                "sha256": sha,
                "size_check_status": size_check_status,
                "download_status": status,
                "failure_reason": failure,
                "license_or_citation": HYDROSHEDS_LICENSE,
                "notes": "Optional fallback/source." if product.optional else "Required or primary full-data source.",
            }
        )

    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "hydrosheds_full_download_inventory.csv")
    _write_csv(frame[["source_id", "product_name", "download_status", "expected_file_size_bytes", "file_size_bytes", "size_check_status", "failure_reason"]], TABLE_DIR / "hydrosheds_full_download_status.csv")
    _mark_superseded_manifest_failures(successful_source_ids)
    free_after = _disk_free_gb(download_root)
    downloaded = frame[frame["download_status"].isin(["downloaded", "already_present"])]
    total_bytes = pd.to_numeric(downloaded["file_size_bytes"], errors="coerce").fillna(0).sum()
    lines = [
        "# HydroSHEDS Full Download Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Summary",
        f"- downloaded_or_present_count: `{len(downloaded)}`",
        f"- failed_count: `{int(frame['download_status'].astype(str).str.contains('failed|manual_required|partial|unpack_failed', regex=True).sum())}`",
        f"- total_downloaded_bytes: `{int(total_bytes)}`",
        f"- disk_free_before_gb: `{free_before}`",
        f"- disk_free_after_gb: `{free_after}`",
        f"- min_free_space_policy_gb: `{min_free}`",
        "",
        "Raw zip, geodatabase, shapefile, and unpacked files remain under `data/raw_external/hydrosheds_full/` and are not committed to git.",
        "",
        "## License Notes",
        HYDROSHEDS_LICENSE,
        "",
        "## Inventory",
        _md_table(frame, max_rows=120),
    ]
    (REPORT_DIR / "hydrosheds_full_download_report.md").write_text("\n".join(lines), encoding="utf-8")
    return frame


def _iter_vector_paths() -> list[Path]:
    config = _load_config()
    roots = [_download_root(config), _unpack_root(config)]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        paths.extend([item for item in root.rglob("*.shp") if item.is_file()])
        paths.extend([item for item in root.rglob("*.gpkg") if item.is_file()])
        paths.extend([item for item in root.rglob("*.geojson") if item.is_file()])
        for item in root.rglob("*.gdb"):
            if item.is_dir() and any(item.glob("*.gdbtable")):
                paths.append(item)
    return sorted(set(paths))


def _classify_vector_path(vector_path: Path) -> dict[str, str]:
    text = vector_path.as_posix().lower()
    name = vector_path.name.lower()
    if "hydrorivers" in text:
        dataset = "hydrorivers"
    elif "basinatlas" in text:
        dataset = "basinatlas"
    elif "riveratlas" in text:
        dataset = "riveratlas"
    elif "lakeatlas" in text:
        dataset = "lakeatlas"
    elif "hybas_lake" in text:
        dataset = "hydrobasins_custom_lakes_full"
    elif "hybas" in text:
        dataset = "hydrobasins_standard_full"
    else:
        dataset = "unknown"
    fmt = "geodatabase" if vector_path.suffix.lower() == ".gdb" else vector_path.suffix.lower().lstrip(".")
    region = ""
    for region_name, code in REGION_CODES.items():
        if re.search(rf"[_/-]{code}[_/-]", text) or f"_{code}_" in text:
            region = region_name
            break
    if not region:
        for region_name, code in HYDRORIVERS_REGIONS.items():
            if code and f"_v10_{code}" in name:
                region = region_name
                break
    if not region and ("global" in text or name in {"hydrorivers_v10.gdb", "hydrorivers_v10_shp.shp"} or "atlas" in text):
        region = "Global"
    level = ""
    match = re.search(r"lev(\d{2})(?:-|_)?(?:\d{2})?", text)
    if match:
        level = match.group(1)
    return {"dataset_family": dataset, "region": region, "format": fmt, "level": level}


def _geo_available() -> tuple[bool, str]:
    try:
        import pyogrio  # noqa: F401
        import shapely  # noqa: F401

        return True, ""
    except Exception as exc:
        return False, str(exc)


def _list_layers(vector_path: Path) -> list[str]:
    import pyogrio

    if vector_path.suffix.lower() == ".shp" or vector_path.suffix.lower() in {".gpkg", ".geojson"}:
        return [vector_path.stem]
    layers = pyogrio.list_layers(vector_path)
    out: list[str] = []
    for layer in layers:
        if not isinstance(layer, str) and hasattr(layer, "__len__") and len(layer):
            out.append(str(layer[0]))
        elif isinstance(layer, (list, tuple)) and layer:
            out.append(str(layer[0]))
        else:
            out.append(str(layer))
    return out


def _layer_info(vector_path: Path, layer_name: str) -> dict[str, Any]:
    import pyogrio

    kwargs = {} if vector_path.suffix.lower() == ".shp" else {"layer": layer_name}
    info = pyogrio.read_info(vector_path, **kwargs)
    fields = [str(item) for item in info.get("fields", [])]
    return {
        "feature_count": info.get("features", ""),
        "geometry_type": info.get("geometry_type", ""),
        "crs": str(info.get("crs") or ""),
        "columns": fields,
    }


def _detect(columns: Iterable[str], candidates: list[str]) -> list[str]:
    lookup = {str(column).lower(): str(column) for column in columns}
    return [lookup[item.lower()] for item in candidates if item.lower() in lookup]


def _index_rows_for_path(vector_path: Path) -> list[dict[str, Any]]:
    meta = _classify_vector_path(vector_path)
    rows: list[dict[str, Any]] = []
    try:
        layers = _list_layers(vector_path)
    except Exception as exc:
        rows.append(
            {
                **meta,
                "local_path": relpath(vector_path),
                "layer_name": "",
                "feature_count": "",
                "geometry_type": "",
                "crs": "",
                "columns_json": "[]",
                "id_columns_detected": "",
                "area_columns_detected": "",
                "pfaf_columns_detected": "",
                "next_down_columns_detected": "",
                "read_status": "failed",
                "failure_reason": str(exc),
            }
        )
        return rows
    for layer in layers:
        try:
            info = _layer_info(vector_path, layer)
            columns = info["columns"]
            level = meta["level"]
            layer_level = re.search(r"lev(?:el)?[_-]?(\d{2})", layer.lower())
            if layer_level:
                level = layer_level.group(1)
            rows.append(
                {
                    **meta,
                    "level": level,
                    "local_path": relpath(vector_path),
                    "layer_name": layer,
                    "feature_count": info["feature_count"],
                    "geometry_type": info["geometry_type"],
                    "crs": info["crs"],
                    "columns_json": json.dumps(columns),
                    "id_columns_detected": ";".join(_detect(columns, KEY_COLUMNS["id"])),
                    "area_columns_detected": ";".join(_detect(columns, KEY_COLUMNS["area"])),
                    "pfaf_columns_detected": ";".join(_detect(columns, KEY_COLUMNS["pfaf"])),
                    "next_down_columns_detected": ";".join(_detect(columns, KEY_COLUMNS["next_down"])),
                    "read_status": "ok",
                    "failure_reason": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    **meta,
                    "local_path": relpath(vector_path),
                    "layer_name": layer,
                    "feature_count": "",
                    "geometry_type": "",
                    "crs": "",
                    "columns_json": "[]",
                    "id_columns_detected": "",
                    "area_columns_detected": "",
                    "pfaf_columns_detected": "",
                    "next_down_columns_detected": "",
                    "read_status": "failed",
                    "failure_reason": str(exc),
                }
            )
    return rows


def index_hydrosheds_full() -> pd.DataFrame:
    ensure_project_dirs()
    available, geo_error = _geo_available()
    vector_paths = _iter_vector_paths()
    rows: list[dict[str, Any]] = []
    if not available:
        rows.append(
            {
                "dataset_family": "all",
                "region": "",
                "format": "",
                "level": "",
                "local_path": "",
                "layer_name": "",
                "feature_count": "",
                "geometry_type": "",
                "crs": "",
                "columns_json": "[]",
                "id_columns_detected": "",
                "area_columns_detected": "",
                "pfaf_columns_detected": "",
                "next_down_columns_detected": "",
                "read_status": "missing_geospatial_dependencies",
                "failure_reason": geo_error,
            }
        )
    elif not vector_paths:
        rows.append(
            {
                "dataset_family": "all",
                "region": "",
                "format": "",
                "level": "",
                "local_path": "",
                "layer_name": "",
                "feature_count": "",
                "geometry_type": "",
                "crs": "",
                "columns_json": "[]",
                "id_columns_detected": "",
                "area_columns_detected": "",
                "pfaf_columns_detected": "",
                "next_down_columns_detected": "",
                "read_status": "manual_required_no_local_files",
                "failure_reason": "No HydroSHEDS/HydroATLAS vector files found under configured download/unpack roots.",
            }
        )
    else:
        for vector_path in vector_paths:
            rows.extend(_index_rows_for_path(vector_path))

    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "hydrosheds_file_index.csv")
    _write_csv(frame[frame["dataset_family"].astype(str).str.contains("hydrobasins", case=False, na=False)], TABLE_DIR / "hydrobasins_layer_index.csv")
    _write_csv(frame[frame["dataset_family"].astype(str).str.contains("hydrorivers", case=False, na=False)], TABLE_DIR / "hydrorivers_layer_index.csv")
    _write_csv(frame[frame["dataset_family"].astype(str).str.contains("atlas", case=False, na=False)], TABLE_DIR / "hydroatlas_layer_index.csv")
    return frame


def _candidate_index(name: str) -> pd.DataFrame:
    frame = _read_csv(TABLE_DIR / name)
    if frame.empty:
        index_hydrosheds_full()
        frame = _read_csv(TABLE_DIR / name)
    return frame


def _as_path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else path(candidate)


def _columns_from_row(row: pd.Series) -> list[str]:
    try:
        return list(json.loads(str(row.get("columns_json", "[]"))))
    except Exception:
        return []


def _pick_col(columns: Iterable[str], candidates: Iterable[str]) -> str:
    lookup = {str(column).lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return ""


def _read_layer(row: pd.Series, *, bbox: tuple[float, float, float, float] | None = None, columns: list[str] | None = None, read_geometry: bool = True) -> Any:
    import pyogrio

    vector_path = _as_path(str(row.get("local_path", "")))
    layer = str(row.get("layer_name", ""))
    kwargs: dict[str, Any] = {"bbox": bbox, "columns": columns, "read_geometry": read_geometry}
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    if vector_path.suffix.lower() != ".shp":
        kwargs["layer"] = layer
    return pyogrio.read_dataframe(vector_path, **kwargs)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_distance_km(geometry: Any, lat: float, lon: float) -> float:
    from shapely.geometry import Point
    from shapely.ops import nearest_points

    point = Point(lon, lat)
    try:
        nearest = nearest_points(point, geometry)[1]
        return _haversine_km(lat, lon, float(nearest.y), float(nearest.x))
    except Exception:
        centroid = geometry.centroid
        return _haversine_km(lat, lon, float(centroid.y), float(centroid.x))


def _station_records() -> list[dict[str, Any]]:
    rows = []
    for river, meta in load_rivers().items():
        rows.append(
            {
                "river": river,
                "station": station_for_river(river),
                "station_lat": meta.get("approximate_station_latitude"),
                "station_lon": meta.get("approximate_station_longitude"),
            }
        )
    return rows


def _hydroriver_layers_for_river(river: str) -> pd.DataFrame:
    index = _candidate_index("hydrorivers_layer_index.csv")
    if index.empty:
        return index
    ok = index[index["read_status"].astype(str).eq("ok")].copy()
    if ok.empty:
        return ok
    preferred = ok[(ok["region"].astype(str).eq("Global")) & (ok["format"].astype(str).eq("geodatabase"))]
    if not preferred.empty:
        return preferred
    hints = RIVER_REGION_HINTS.get(river, [])
    hinted = ok[ok["region"].astype(str).isin(hints)]
    return hinted if not hinted.empty else ok


def match_stations_to_hydrorivers(max_distance_km: float = 50.0) -> pd.DataFrame:
    ensure_project_dirs()
    rows: list[dict[str, Any]] = []
    available, geo_error = _geo_available()
    for station in _station_records():
        river = station["river"]
        lat = float(station["station_lat"])
        lon = float(station["station_lon"])
        base = {
            **station,
            "matched_hyriv_id": "",
            "matched_hybas_id": "",
            "matched_reach_name": "",
            "matched_main_riv": "",
            "ord_stra": "",
            "dis_av_cms": "",
            "length_km": "",
            "dist_dn_km": "",
            "snap_distance_km": "",
            "hydrorivers_source_path": "",
            "match_status": "failed",
            "quality_flag": "failed_hydroriver_match",
            "notes": "",
        }
        if not available:
            base["notes"] = f"Missing geospatial dependencies: {geo_error}"
            rows.append(base)
            continue
        layers = _hydroriver_layers_for_river(river)
        if layers.empty:
            base["notes"] = "No readable HydroRIVERS layers indexed."
            rows.append(base)
            continue
        best: dict[str, Any] | None = None
        for _, layer in layers.iterrows():
            columns = _columns_from_row(layer)
            wanted = [col for col in columns if col in set(KEY_COLUMNS["river"] + KEY_COLUMNS["id"])]
            radius_deg = max(0.5, max_distance_km / 70.0)
            try:
                candidates = _read_layer(layer, bbox=(lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg), columns=wanted or None, read_geometry=True)
            except Exception:
                continue
            if candidates.empty:
                continue
            if candidates.crs and str(candidates.crs).lower() not in {"epsg:4326", "ogc:crs84", "wgs84"}:
                try:
                    candidates = candidates.to_crs(4326)
                except Exception:
                    pass
            col_hyriv = _pick_col(candidates.columns, ["HYRIV_ID", "OBJECTID"])
            col_hybas = _pick_col(candidates.columns, ["HYBAS_ID", "BAS_ID"])
            col_order = _pick_col(candidates.columns, ["ORD_STRA", "ORD_FLOW", "ORDER"])
            col_dis = _pick_col(candidates.columns, ["DIS_AV_CMS", "DIS_AVG_CMS", "DIS_AV_C"])
            col_length = _pick_col(candidates.columns, ["LENGTH_KM"])
            col_dist = _pick_col(candidates.columns, ["DIST_DN_KM", "DIST_DN"])
            col_main = _pick_col(candidates.columns, ["MAIN_RIV", "RIV_NAME"])
            for _, candidate in candidates.iterrows():
                if candidate.geometry is None or candidate.geometry.is_empty:
                    continue
                distance = _nearest_distance_km(candidate.geometry, lat, lon)
                if distance > max_distance_km:
                    continue
                order = pd.to_numeric(pd.Series([candidate.get(col_order, "")]), errors="coerce").iloc[0] if col_order else 0
                discharge = pd.to_numeric(pd.Series([candidate.get(col_dis, "")]), errors="coerce").iloc[0] if col_dis else 0
                score = distance - (float(order) if pd.notna(order) else 0) * 0.5 - math.log10(max(float(discharge), 0) + 1) * 2
                record = {
                    **base,
                    "matched_hyriv_id": candidate.get(col_hyriv, "") if col_hyriv else "",
                    "matched_hybas_id": candidate.get(col_hybas, "") if col_hybas else "",
                    "matched_reach_name": candidate.get(col_main, "") if col_main else "",
                    "matched_main_riv": candidate.get(col_main, "") if col_main else "",
                    "ord_stra": candidate.get(col_order, "") if col_order else "",
                    "dis_av_cms": candidate.get(col_dis, "") if col_dis else "",
                    "length_km": candidate.get(col_length, "") if col_length else "",
                    "dist_dn_km": candidate.get(col_dist, "") if col_dist else "",
                    "snap_distance_km": round(float(distance), 3),
                    "hydrorivers_source_path": layer.get("local_path", ""),
                    "match_status": "matched",
                    "quality_flag": "snap_distance_needs_review" if distance > 25 else "matched_hydroriver",
                    "notes": "Nearest HydroRIVERS reach selected with distance, stream order, and discharge tie-breakers.",
                    "_score": score,
                }
                if best is None or record["_score"] < best["_score"]:
                    best = record
        if best is None:
            base["notes"] = f"No HydroRIVERS reach within {max_distance_km} km."
            rows.append(base)
        else:
            best.pop("_score", None)
            rows.append(best)
    frame = pd.DataFrame(rows)
    _write_csv(frame, TABLE_DIR / "station_to_hydroriver_match.csv")
    lines = [
        "# Station To HydroRIVERS Match Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Matches",
        _md_table(frame),
    ]
    (REPORT_DIR / "station_to_hydroriver_match_report.md").write_text("\n".join(lines), encoding="utf-8")
    return frame


def _hydrobasin_layers_for_river(river: str, level: int) -> pd.DataFrame:
    index = _candidate_index("hydrobasins_layer_index.csv")
    if index.empty:
        return index
    ok = index[(index["read_status"].astype(str).eq("ok")) & (index["dataset_family"].astype(str).eq("hydrobasins_standard_full"))].copy()
    if ok.empty:
        return ok
    level_text = f"{level:02d}"
    ok = ok[ok["level"].astype(str).str.zfill(2).eq(level_text)]
    if ok.empty:
        return ok
    hints = RIVER_REGION_HINTS.get(river, [])
    hinted = ok[ok["region"].astype(str).isin(hints)]
    return hinted if not hinted.empty else ok


def _point_in_basin(layer: pd.Series, lat: float, lon: float, search_radius_km: float = 50.0) -> tuple[dict[str, Any] | None, str]:
    from shapely.geometry import Point

    columns = _columns_from_row(layer)
    wanted = [col for col in columns if col in set(KEY_COLUMNS["id"] + KEY_COLUMNS["area"] + KEY_COLUMNS["pfaf"] + KEY_COLUMNS["next_down"])]
    try:
        candidates = _read_layer(layer, bbox=(lon - 1.0, lat - 1.0, lon + 1.0, lat + 1.0), columns=wanted or None, read_geometry=True)
    except Exception as exc:
        return None, str(exc)
    if candidates.empty:
        return None, "No polygons returned in station bbox."
    if candidates.crs and str(candidates.crs).lower() not in {"epsg:4326", "ogc:crs84", "wgs84"}:
        try:
            candidates = candidates.to_crs(4326)
        except Exception:
            pass
    point = Point(lon, lat)
    candidates = candidates.copy()
    try:
        candidates["_contains_station"] = candidates.geometry.contains(point) | candidates.geometry.touches(point)
    except Exception:
        candidates["_contains_station"] = False
    candidates["_distance"] = candidates.geometry.apply(lambda geom: _nearest_distance_km(geom, lat, lon))
    col_up_area = _pick_col(candidates.columns, ["UP_AREA"])
    col_sub_area = _pick_col(candidates.columns, ["SUB_AREA", "AREA_SQKM"])
    score_area_col = col_up_area or col_sub_area
    if score_area_col:
        candidates["_score_area"] = pd.to_numeric(candidates[score_area_col], errors="coerce").fillna(0)
    else:
        candidates["_score_area"] = 0
    nearby = candidates[candidates["_distance"] <= search_radius_km]
    if not nearby.empty and nearby["_score_area"].max() > 10000:
        matched = nearby.sort_values(["_score_area", "_distance"], ascending=[False, True]).head(1)
        method = "nearby_mainstem_upstream_area_preferred"
    else:
        contained = candidates[candidates["_contains_station"]]
        if not contained.empty:
            matched = contained.sort_values(["_score_area", "_distance"], ascending=[False, True]).head(1)
            method = "point_in_polygon"
        else:
            matched = candidates.sort_values("_distance").head(1)
            method = "nearest_polygon"
    if matched.empty:
        return None, "No point-in-polygon or nearest basin candidate."
    row = matched.iloc[0]
    col_id = _pick_col(matched.columns, ["HYBAS_ID", "BAS_ID", "OBJECTID"])
    col_pfaf = _pick_col(matched.columns, ["PFAF_ID", "PFAF"])
    col_area = _pick_col(matched.columns, ["SUB_AREA", "AREA_SQKM", "UP_AREA"])
    selected_distance = float(row.get("_distance", math.nan)) if pd.notna(row.get("_distance", math.nan)) else math.nan
    return {
        "matched_hybas_id": row.get(col_id, "") if col_id else "",
        "matched_pfaf_id": row.get(col_pfaf, "") if col_pfaf else "",
        "local_basin_area_km2": row.get(col_area, "") if col_area else "",
        "match_method": method,
        "hydrobasins_source_path": layer.get("local_path", ""),
        "quality_flag": "matched_hydrobasin" if method in {"point_in_polygon", "nearby_mainstem_upstream_area_preferred"} and (math.isnan(selected_distance) or selected_distance <= 25) else "nearest_basin_needs_review",
        "notes": f"HydroBASINS standard layer match; distance_km={selected_distance:.3f}; method={method}.",
    }, ""


def match_stations_to_hydrobasins(levels: Iterable[int] = (6, 7, 8, 9)) -> pd.DataFrame:
    ensure_project_dirs()
    rows: list[dict[str, Any]] = []
    available, geo_error = _geo_available()
    for station in _station_records():
        river = station["river"]
        for level in levels:
            base = {
                **station,
                "matched_hybas_id": "",
                "matched_pfaf_id": "",
                "basin_level": level,
                "local_basin_area_km2": "",
                "match_method": "",
                "hydrobasins_source_path": "",
                "quality_flag": "failed_basin_match",
                "match_status": "failed",
                "selected_primary": False,
                "notes": "",
            }
            if not available:
                base["notes"] = f"Missing geospatial dependencies: {geo_error}"
                rows.append(base)
                continue
            layers = _hydrobasin_layers_for_river(river, level)
            if layers.empty:
                base["notes"] = f"No readable HydroBASINS standard level {level:02d} layer indexed."
                rows.append(base)
                continue
            matched_record = None
            failures = []
            for _, layer in layers.iterrows():
                matched_record, failure = _point_in_basin(layer, float(station["station_lat"]), float(station["station_lon"]))
                if matched_record:
                    break
                if failure:
                    failures.append(failure)
            if matched_record:
                base.update(matched_record)
                base["match_status"] = "matched"
            else:
                base["notes"] = "; ".join(failures[:3]) or "No basin match."
            rows.append(base)
    frame = pd.DataFrame(rows)
    for river in frame["river"].dropna().unique():
        matched = frame[(frame["river"].eq(river)) & (frame["match_status"].eq("matched"))].copy()
        if matched.empty:
            continue
        preferred = matched[matched["basin_level"].astype(str).eq("7")]
        selected_index = preferred.index[0] if not preferred.empty else matched.index[0]
        frame.loc[selected_index, "selected_primary"] = True
    _write_csv(frame, TABLE_DIR / "station_to_hydrobasin_match.csv")
    return frame


def _read_basin_topology(layer_row: pd.Series) -> tuple[pd.DataFrame, dict[str, str]]:
    columns = _columns_from_row(layer_row)
    id_col = _pick_col(columns, ["HYBAS_ID", "BAS_ID"])
    next_col = _pick_col(columns, ["NEXT_DOWN"])
    pfaf_col = _pick_col(columns, ["PFAF_ID", "PFAF"])
    sub_area_col = _pick_col(columns, ["SUB_AREA", "AREA_SQKM"])
    up_area_col = _pick_col(columns, ["UP_AREA"])
    wanted = [col for col in [id_col, next_col, pfaf_col, sub_area_col, up_area_col] if col]
    frame = _read_layer(layer_row, columns=wanted, read_geometry=False)
    return frame, {"id": id_col, "next": next_col, "pfaf": pfaf_col, "sub_area": sub_area_col, "up_area": up_area_col}


def _upstream_ids(frame: pd.DataFrame, id_col: str, next_col: str, outlet_id: str) -> set[str]:
    def id_text(value: Any) -> str:
        numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.notna(numeric) and float(numeric).is_integer():
            return str(int(numeric))
        return str(value)

    reverse: dict[str, list[str]] = {}
    for _, row in frame.iterrows():
        node = id_text(row.get(id_col, ""))
        down = id_text(row.get(next_col, ""))
        if not node:
            continue
        reverse.setdefault(down, []).append(node)
    outlet = id_text(outlet_id)
    seen = {outlet}
    queue: deque[str] = deque([outlet])
    while queue:
        current = queue.popleft()
        for upstream in reverse.get(current, []):
            if upstream not in seen:
                seen.add(upstream)
                queue.append(upstream)
    return seen


def build_upstream_basin_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_project_dirs()
    matches = _read_csv(TABLE_DIR / "station_to_hydrobasin_match.csv")
    if matches.empty:
        matches = match_stations_to_hydrobasins()
    agg_rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    selected = matches[matches.get("selected_primary", pd.Series(dtype=bool)).astype(str).str.lower().isin(["true", "1"])] if not matches.empty else pd.DataFrame()
    for station in _station_records():
        river = station["river"]
        base = {
            "river": river,
            "station": station["station"],
            "basin_level": "",
            "matched_hybas_id": "",
            "matched_pfaf_id": "",
            "n_upstream_subbasins": 0,
            "upstream_basin_ids_json": "[]",
            "upstream_area_km2": "",
            "local_basin_area_km2": "",
            "aggregation_method": "",
            "topology_fields_used": "",
            "aggregation_status": "upstream_aggregation_failed",
            "quality_flag": "failed_basin_match",
            "notes": "",
        }
        row = selected[selected["river"].astype(str).eq(river)]
        if row.empty:
            base["notes"] = "No selected primary HydroBASINS match."
            agg_rows.append(base)
            continue
        match = row.iloc[0]
        layer_path = str(match.get("hydrobasins_source_path", ""))
        layer_index = _candidate_index("hydrobasins_layer_index.csv")
        layer = layer_index[layer_index["local_path"].astype(str).eq(layer_path)]
        if layer.empty:
            base["notes"] = "Selected HydroBASINS layer is missing from index."
            agg_rows.append(base)
            continue
        try:
            topo, cols = _read_basin_topology(layer.iloc[0])
            if not cols["id"] or not cols["next"]:
                raise ValueError("HYBAS_ID/NEXT_DOWN topology fields not detected.")
            outlet = str(match.get("matched_hybas_id", ""))
            upstream = _upstream_ids(topo, cols["id"], cols["next"], outlet)
            members = topo[topo[cols["id"]].astype(str).isin(upstream)].copy()
            if members.empty:
                raise ValueError("Topology traversal returned no upstream members.")
            area_col = cols["sub_area"] or cols["up_area"]
            upstream_area = pd.to_numeric(members[area_col], errors="coerce").sum() if area_col else math.nan
            local_area = pd.to_numeric(pd.Series([match.get("local_basin_area_km2", "")]), errors="coerce").iloc[0]
            pfaf = str(match.get("matched_pfaf_id", ""))
            quality = "upstream_basin_complete"
            notes = "Upstream set traversed with NEXT_DOWN topology."
            if pd.notna(upstream_area) and upstream_area < 10000:
                quality = "upstream_area_plausibility_warning"
                notes += " Upstream area is below 10,000 km2 for a major river and needs review."
            base.update(
                {
                    "basin_level": match.get("basin_level", ""),
                    "matched_hybas_id": outlet,
                    "matched_pfaf_id": pfaf,
                    "n_upstream_subbasins": len(members),
                    "upstream_basin_ids_json": json.dumps(sorted(upstream)),
                    "upstream_area_km2": float(upstream_area) if pd.notna(upstream_area) else "",
                    "local_basin_area_km2": float(local_area) if pd.notna(local_area) else "",
                    "aggregation_method": "NEXT_DOWN_reverse_graph",
                    "topology_fields_used": f"{cols['id']};{cols['next']};{area_col}",
                    "aggregation_status": "complete",
                    "quality_flag": quality,
                    "notes": notes,
                }
            )
            for _, member in members.iterrows():
                member_rows.append(
                    {
                        "river": river,
                        "station": station["station"],
                        "basin_level": match.get("basin_level", ""),
                        "matched_hybas_id": outlet,
                        "upstream_hybas_id": member.get(cols["id"], ""),
                        "next_down": member.get(cols["next"], ""),
                        "sub_area_km2": member.get(area_col, "") if area_col else "",
                        "pfaf_id": member.get(cols["pfaf"], "") if cols["pfaf"] else "",
                        "hydrobasins_source_path": layer_path,
                    }
                )
        except Exception as exc:
            base.update(
                {
                    "basin_level": match.get("basin_level", ""),
                    "matched_hybas_id": match.get("matched_hybas_id", ""),
                    "matched_pfaf_id": match.get("matched_pfaf_id", ""),
                    "local_basin_area_km2": match.get("local_basin_area_km2", ""),
                    "quality_flag": "upstream_aggregation_failed",
                    "notes": str(exc),
                }
            )
        agg_rows.append(base)
    agg = pd.DataFrame(agg_rows)
    membership = pd.DataFrame(member_rows)
    _write_csv(agg, TABLE_DIR / "upstream_basin_aggregation.csv")
    _write_csv(membership, TABLE_DIR / "upstream_basin_membership.csv")
    lines = [
        "# Upstream Basin Aggregation Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Aggregation Summary",
        _md_table(agg),
        "",
        "## Method",
        "Upstream membership is computed with reverse traversal of HydroBASINS `NEXT_DOWN` topology from the station-matched `HYBAS_ID`. ROI area is not used as upstream area.",
    ]
    (REPORT_DIR / "upstream_basin_aggregation_report.md").write_text("\n".join(lines), encoding="utf-8")
    return agg, membership


def _atlas_layer(kind: str, basin_level: str | int | None = None) -> pd.Series | None:
    index = _candidate_index("hydroatlas_layer_index.csv")
    if index.empty:
        return None
    ok = index[(index["read_status"].astype(str).eq("ok")) & (index["dataset_family"].astype(str).eq(kind))]
    if ok.empty:
        return None
    if basin_level is not None and kind == "basinatlas":
        level_text = f"{int(basin_level):02d}" if str(basin_level).isdigit() else str(basin_level).zfill(2)
        level_match = ok[ok["layer_name"].astype(str).str.lower().str.contains(f"lev{level_text}|level{level_text}", regex=True)]
        if not level_match.empty:
            return level_match.iloc[0]
    return ok.iloc[0]


def _read_atlas_subset(layer: pd.Series, id_column_candidates: list[str], ids: list[str], extra_columns: list[str] | None = None) -> pd.DataFrame:
    columns = _columns_from_row(layer)
    id_col = _pick_col(columns, id_column_candidates)
    if not id_col:
        return pd.DataFrame()
    wanted = [id_col]
    if extra_columns:
        wanted.extend([col for col in extra_columns if col in columns and col not in wanted])
    else:
        wanted.extend([col for col in columns if col != id_col][:120])
    frames = []
    for start in range(0, len(ids), 800):
        chunk = [str(item) for item in ids[start : start + 800] if str(item)]
        if not chunk:
            continue
        quoted = ",".join(f"'{item}'" for item in chunk)
        numeric = ",".join(item for item in chunk if re.fullmatch(r"-?\d+(?:\.\d+)?", item))
        where_candidates = [f"{id_col} IN ({quoted})"]
        if numeric:
            where_candidates.append(f"{id_col} IN ({numeric})")
        try:
            import pyogrio

            vector_path = _as_path(str(layer.get("local_path", "")))
            frame = pd.DataFrame()
            for where in where_candidates:
                kwargs: dict[str, Any] = {"where": where, "columns": wanted, "read_geometry": False}
                if vector_path.suffix.lower() != ".shp":
                    kwargs["layer"] = str(layer.get("layer_name", ""))
                try:
                    frame = pyogrio.read_dataframe(vector_path, **kwargs)
                except Exception:
                    frame = pd.DataFrame()
                if not frame.empty:
                    break
            if not frame.empty and id_col in frame.columns:
                frame = frame[frame[id_col].astype(str).isin(chunk)]
        except Exception:
            frame = pd.DataFrame()
        if not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _summarize_attributes(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    summary: dict[str, Any] = {"rows_matched": int(len(frame)), "columns_available": int(len(frame.columns))}
    numeric = frame.select_dtypes(include="number")
    for column in list(numeric.columns)[:40]:
        values = pd.to_numeric(numeric[column], errors="coerce")
        if values.notna().any():
            summary[f"{column}_mean"] = float(values.mean())
    summary["sample_columns"] = list(frame.columns[:40])
    return summary


def _write_basin_context_from_outputs(agg: pd.DataFrame, basin_attrs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    attr_lookup = {str(row["river"]): row for _, row in basin_attrs.iterrows()} if not basin_attrs.empty and "river" in basin_attrs.columns else {}
    for _, row in agg.iterrows():
        river = str(row.get("river", ""))
        attr_row = attr_lookup.get(river)
        hydro_json = "{}"
        landcover_json = "{}"
        attr_source = ""
        quality = "failed_basin_match"
        if str(row.get("aggregation_status", "")) == "complete":
            quality = "upstream_basin_complete_attributes_missing"
            if attr_row is not None:
                hydro_json = str(attr_row.get("hydroatlas_attributes_json", "{}"))
                landcover_json = str(attr_row.get("landcover_attributes_json", "{}"))
                attr_source = str(attr_row.get("attribute_source", ""))
                if hydro_json and hydro_json != "{}":
                    quality = "upstream_basin_complete_attributes_partial"
                    if landcover_json and landcover_json != "{}":
                        quality = "upstream_basin_complete_with_hydroatlas"
        rows.append(
            {
                "river": river,
                "basin_id": row.get("matched_hybas_id", ""),
                "geometry_source": "HydroBASINS standard NEXT_DOWN upstream aggregation",
                "upstream_area_km2": row.get("upstream_area_km2", ""),
                "pfaf_id": row.get("matched_pfaf_id", ""),
                "attribute_source": attr_source or "HydroATLAS attributes unavailable or not extracted",
                "hydroatlas_attributes_json": hydro_json,
                "landcover_attributes_json": landcover_json,
                "climate_aggregation_notes": "Use upstream HydroBASINS membership for future basin-level aggregation; daily hydroclimate table may still use ROI aggregation where noted.",
                "source_id": "hydrobasins_standard_full;basinatlas_global_gdb;riveratlas_global_gdb",
                "quality_flag": quality,
                "notes": row.get("notes", ""),
            }
        )
    frame = ensure_columns(pd.DataFrame(rows), "basin_context_canonical")
    write_table(frame, "basin_context_canonical", PROCESSED_DIR / "basin_context_canonical.csv")
    acceptable = {"upstream_basin_complete_with_hydroatlas", "upstream_basin_complete_attributes_partial"}
    all_six = set(frame["river"].astype(str)) == set(load_rivers().keys())
    upstream_complete = all_six and frame["quality_flag"].astype(str).str.startswith("upstream_basin_complete").all()
    publication = upstream_complete and set(frame["quality_flag"].astype(str)).issubset(acceptable)
    if publication and (frame["quality_flag"].astype(str) == "upstream_basin_complete_with_hydroatlas").all():
        status = "upstream_basin_complete_with_hydroatlas"
    elif publication:
        status = "upstream_basin_complete_attributes_partial"
    elif upstream_complete:
        status = "upstream_basin_complete_attributes_missing"
    else:
        status = "manual_required"
    status_frame = pd.DataFrame(
        [
            {
                "basin_context_status": status,
                "n_rivers": len(frame),
                "n_upstream_complete": int(frame["quality_flag"].astype(str).str.startswith("upstream_basin_complete").sum()) if not frame.empty else 0,
                "accepted_for_full_training_readiness": True,
                "accepted_for_core_full_training_readiness": True,
                "accepted_for_publication_grade_training": bool(publication),
                "quality_flag": status,
                "notes": "Publication-grade basin context requires upstream HydroBASINS membership and HydroATLAS attributes for all six rivers.",
            }
        ]
    )
    _write_csv(status_frame, TABLE_DIR / "basin_context_status.csv")
    lines = [
        "# Basin Context Report",
        "",
        f"Generated: {utc_now()}",
        "",
        NO_MODEL_TEXT,
        "",
        "## Status",
        _md_table(status_frame),
        "",
        "## Canonical Basin Context",
        _md_table(frame),
    ]
    (REPORT_DIR / "basin_context_report.md").write_text("\n".join(lines), encoding="utf-8")
    return frame


def extract_hydroatlas_attributes() -> pd.DataFrame:
    ensure_project_dirs()
    agg = _read_csv(TABLE_DIR / "upstream_basin_aggregation.csv")
    membership = _read_csv(TABLE_DIR / "upstream_basin_membership.csv")
    if agg.empty or membership.empty:
        agg, membership = build_upstream_basin_context()
    basin_rows: list[dict[str, Any]] = []
    river_rows: list[dict[str, Any]] = []
    lake_rows: list[dict[str, Any]] = []
    for _, row in agg.iterrows():
        river = str(row.get("river", ""))
        level = row.get("basin_level", "")
        ids = membership[membership["river"].astype(str).eq(river)]["upstream_hybas_id"].astype(str).tolist() if not membership.empty else []
        basin_layer = _atlas_layer("basinatlas", level)
        basin_frame = _read_atlas_subset(basin_layer, ["HYBAS_ID", "BAS_ID"], ids) if basin_layer is not None and ids else pd.DataFrame()
        basin_summary = _summarize_attributes(basin_frame)
        landcover = {key: value for key, value in basin_summary.items() if "lc_" in key.lower() or "land" in key.lower() or "for_" in key.lower()}
        basin_rows.append(
            {
                "river": river,
                "basin_level": level,
                "n_upstream_subbasins": row.get("n_upstream_subbasins", ""),
                "attribute_source": basin_layer.get("local_path", "") if basin_layer is not None else "",
                "rows_matched": len(basin_frame),
                "hydroatlas_attributes_json": json.dumps(basin_summary, ensure_ascii=False),
                "landcover_attributes_json": json.dumps(landcover, ensure_ascii=False),
                "extraction_status": "attributes_extracted_not_fully_aggregated" if basin_summary else "attributes_missing",
                "notes": "Numeric BasinATLAS columns summarized by simple means; retain upstream membership for future area-weighted aggregation.",
            }
        )
    hydroriver_match = _read_csv(TABLE_DIR / "station_to_hydroriver_match.csv")
    river_layer = _atlas_layer("riveratlas")
    if river_layer is not None and not hydroriver_match.empty:
        ids = hydroriver_match["matched_hyriv_id"].astype(str).tolist()
        river_frame = _read_atlas_subset(river_layer, ["HYRIV_ID"], ids)
        for _, match in hydroriver_match.iterrows():
            hyriv_id = str(match.get("matched_hyriv_id", ""))
            subset = river_frame[river_frame.astype(str).eq(hyriv_id).any(axis=1)] if not river_frame.empty else pd.DataFrame()
            river_rows.append(
                {
                    "river": match.get("river", ""),
                    "station": match.get("station", ""),
                    "matched_hyriv_id": hyriv_id,
                    "attribute_source": river_layer.get("local_path", ""),
                    "attributes_json": json.dumps(_summarize_attributes(subset), ensure_ascii=False),
                    "extraction_status": "extracted" if not subset.empty else "attributes_missing",
                }
            )
    else:
        for station in _station_records():
            river_rows.append(
                {
                    "river": station["river"],
                    "station": station["station"],
                    "matched_hyriv_id": "",
                    "attribute_source": "",
                    "attributes_json": "{}",
                    "extraction_status": "riveratlas_missing",
                }
            )
    lake_layer = _atlas_layer("lakeatlas")
    for river in load_rivers().keys():
        lake_rows.append(
            {
                "river": river,
                "attribute_source": lake_layer.get("local_path", "") if lake_layer is not None else "",
                "attributes_json": "{}",
                "extraction_status": "optional_not_extracted" if lake_layer is not None else "lakeatlas_missing_optional",
            }
        )
    basin_attrs = pd.DataFrame(basin_rows)
    _write_csv(basin_attrs, TABLE_DIR / "hydroatlas_attributes_by_river.csv")
    _write_csv(pd.DataFrame(river_rows), TABLE_DIR / "riveratlas_attributes_by_station.csv")
    _write_csv(pd.DataFrame(lake_rows), TABLE_DIR / "lakeatlas_attributes_by_upstream_basin.csv")
    frame = _write_basin_context_from_outputs(agg, basin_attrs)
    return frame


def build_basin_context_from_hydrosheds() -> pd.DataFrame:
    match_stations_to_hydrorivers()
    match_stations_to_hydrobasins()
    build_upstream_basin_context()
    return extract_hydroatlas_attributes()
