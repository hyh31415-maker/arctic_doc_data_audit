from __future__ import annotations

from ..manifest import append_manifest, source_by_id
from ..paths import path


def gee_hydroclimate_dry_run(source_ids: list[str] | None = None, rivers: str = "all", years: str = "", roi_set: str = "default", report_only: bool = True) -> None:
    ids = source_ids or ["gee_era5_land", "gee_modis_mod10a1", "gee_smap_context_optional"]
    for source_id in ids:
        record = source_by_id(source_id)
        destination = path(record.get("local_subdir", "data/interim/gee_hydroclimate")) / f"{source_id}_dry_run_plan.json"
        append_manifest(
            {
                "source_id": source_id,
                "source_url": record["source_url"],
                "resolved_url": record["source_url"],
                "download_url": ",".join(record.get("gee_collections", [])),
                "retrieved_at_utc": "",
                "local_path": str(destination),
                "file_name": destination.name,
                "file_size_bytes": "",
                "sha256": "",
                "version_detected": "gee_collection",
                "download_status": "report_only" if report_only else "dry_run",
                "failure_reason": f"Earth Engine hydroclimate extraction not executed. rivers={rivers}; years={years}; roi_set={roi_set}.",
                "license_or_citation": "Google Earth Engine source catalog; preserve collection and date.",
                "commit_raw_data": False,
            }
        )

