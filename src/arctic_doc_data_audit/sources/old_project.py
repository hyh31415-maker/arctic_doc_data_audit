from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..manifest import append_manifest, manifest_failure, manifest_for_file, source_by_id
from ..paths import path


def import_old_project_reference(dry_run: bool = False) -> None:
    record = source_by_id("old_arctic_doc_snowmelt_outputs")
    old_project = os.environ.get("OLD_PROJECT_DIR")
    if not old_project:
        append_manifest(
            manifest_failure(
                source_id=record["source_id"],
                source_url=record["source_url"],
                failure_reason="OLD_PROJECT_DIR is not set; old reference import skipped.",
                license_or_citation="Local old project reference only.",
            )
        )
        return
    old_root = Path(old_project)
    if not old_root.exists():
        append_manifest(
            manifest_failure(
                source_id=record["source_id"],
                source_url=record["source_url"],
                failure_reason=f"OLD_PROJECT_DIR does not exist: {old_root}",
                license_or_citation="Local old project reference only.",
            )
        )
        return
    destination_root = path(record.get("local_subdir", "data/interim/reference_old_project"))
    for relative in record.get("selected_files", []):
        source = old_root / relative
        destination = destination_root / relative
        if dry_run:
            append_manifest(
                {
                    "source_id": record["source_id"],
                    "source_url": str(old_root),
                    "resolved_url": str(source),
                    "download_url": f"local-copy:{source}",
                    "retrieved_at_utc": "",
                    "local_path": str(destination),
                    "file_name": destination.name,
                    "file_size_bytes": "",
                    "sha256": "",
                    "version_detected": "",
                    "download_status": "dry_run",
                    "failure_reason": "",
                    "license_or_citation": "Local old project reference only.",
                    "commit_raw_data": False,
                }
            )
            continue
        if not source.exists():
            append_manifest(
                manifest_failure(
                    source_id=record["source_id"],
                    source_url=str(old_root),
                    download_url=f"local-copy:{source}",
                    failure_reason="Selected old reference file not found.",
                    local_path=destination,
                    license_or_citation="Local old project reference only.",
                )
            )
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        append_manifest(
            manifest_for_file(
                source_id=record["source_id"],
                source_url=str(old_root),
                download_url=f"local-copy:{source}",
                resolved_url=str(source),
                local_path=destination,
                version_detected="reference_only",
                license_or_citation="Local old project reference only.",
            )
        )

