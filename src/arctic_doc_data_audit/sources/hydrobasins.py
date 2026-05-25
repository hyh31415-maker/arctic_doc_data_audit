from __future__ import annotations

import json

import yaml

from ..manifest import append_manifest, source_by_id
from ..paths import CONFIG_DIR, path


def acquire_hydrosheds_context(dry_run: bool = True) -> None:
    local_config = CONFIG_DIR / "local_paths.yaml"
    local_paths = {}
    if local_config.exists():
        local_paths = yaml.safe_load(local_config.read_text(encoding="utf-8")) or {}
    for source_id in ["hydrobasins", "hydroatlas"]:
        record = source_by_id(source_id)
        configured = local_paths.get(source_id, {}).get("local_path") if local_paths else ""
        destination = path(record.get("local_subdir", "data/raw_external/hydrosheds")) / f"{source_id}_acquisition_instructions.json"
        append_manifest(
            {
                "source_id": source_id,
                "source_url": record["source_url"],
                "resolved_url": configured or record["source_url"],
                "download_url": configured or record["source_url"],
                "retrieved_at_utc": "",
                "local_path": configured or str(destination),
                "file_name": str(configured).split("/")[-1] if configured else destination.name,
                "file_size_bytes": "",
                "sha256": "",
                "version_detected": "manual_local_file" if configured else "",
                "download_status": "local_path_configured" if configured else ("dry_run" if dry_run else "manual_required"),
                "failure_reason": "Large HydroSHEDS products require size/license review; provide local files via configs/local_paths.yaml.",
                "license_or_citation": "HydroSHEDS HydroBASINS/HydroATLAS; verify license before redistribution.",
                "commit_raw_data": False,
            }
        )
        if not dry_run and not configured:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps({"source_id": source_id, "instructions": record["notes"]}, indent=2), encoding="utf-8")

