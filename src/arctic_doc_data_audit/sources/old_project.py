from __future__ import annotations

import os
import shutil
from fnmatch import fnmatch
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
        source_ref = f"env:OLD_PROJECT_DIR/{relative}"
        if dry_run:
            append_manifest(
                {
                    "source_id": record["source_id"],
                    "source_url": "env:OLD_PROJECT_DIR",
                    "resolved_url": source_ref,
                    "download_url": f"local-copy:{source_ref}",
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
                    source_url="env:OLD_PROJECT_DIR",
                    download_url=f"local-copy:{source_ref}",
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
                source_url="env:OLD_PROJECT_DIR",
                download_url=f"local-copy:{source_ref}",
                resolved_url=source_ref,
                local_path=destination,
                version_detected="reference_only",
                license_or_citation="Local old project reference only.",
            )
        )


def _old_project_root(record: dict[str, object]) -> Path | None:
    old_project = os.environ.get("OLD_PROJECT_DIR")
    if not old_project:
        append_manifest(
            manifest_failure(
                source_id=str(record["source_id"]),
                source_url=str(record["source_url"]),
                failure_reason="OLD_PROJECT_DIR is not set; old project import skipped.",
                license_or_citation="Local old project reference only.",
            )
        )
        return None
    old_root = Path(old_project)
    if not old_root.exists():
        append_manifest(
            manifest_failure(
                source_id=str(record["source_id"]),
                source_url=str(record["source_url"]),
                failure_reason=f"OLD_PROJECT_DIR does not exist: env:OLD_PROJECT_DIR",
                license_or_citation="Local old project reference only.",
            )
        )
        return None
    return old_root


def _excluded(path_value: Path, patterns: list[str]) -> bool:
    name = path_value.name.lower()
    relative = path_value.as_posix().lower()
    return any(fnmatch(name, pattern.lower()) or fnmatch(relative, pattern.lower()) for pattern in patterns)


def import_old_project_untrained_data(dry_run: bool = False) -> None:
    record = source_by_id("old_arctic_doc_snowmelt_untrained_data")
    old_root = _old_project_root(record)
    if old_root is None:
        return
    destination_root = path(str(record.get("local_subdir", "data/raw_external/old_project_snapshot")))
    include_dirs = [Path(value) for value in record.get("include_dirs", [])]
    exclude_patterns = [str(value) for value in record.get("exclude_name_patterns", [])]
    copied = 0
    for include_dir in include_dirs:
        source_dir = old_root / include_dir
        if not source_dir.exists():
            append_manifest(
                manifest_failure(
                    source_id=record["source_id"],
                    source_url="env:OLD_PROJECT_DIR",
                    download_url=f"local-copy:env:OLD_PROJECT_DIR/{include_dir.as_posix()}",
                    failure_reason="Configured old project data directory does not exist.",
                    local_path=destination_root / include_dir,
                    license_or_citation="Local old project untrained data snapshot; reference only.",
                )
            )
            continue
        for source in sorted(source_dir.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(old_root)
            if _excluded(relative, exclude_patterns):
                continue
            destination = destination_root / relative
            source_ref = f"env:OLD_PROJECT_DIR/{relative.as_posix()}"
            if dry_run:
                append_manifest(
                    {
                        "source_id": record["source_id"],
                        "source_url": "env:OLD_PROJECT_DIR",
                        "resolved_url": source_ref,
                        "download_url": f"local-copy:{source_ref}",
                        "retrieved_at_utc": "",
                        "local_path": str(destination),
                        "file_name": destination.name,
                        "file_size_bytes": "",
                        "sha256": "",
                        "version_detected": "old_project_snapshot",
                        "download_status": "dry_run",
                        "failure_reason": "",
                        "license_or_citation": "Local old project untrained data snapshot; reference only.",
                        "commit_raw_data": False,
                    }
                )
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            append_manifest(
                manifest_for_file(
                    source_id=record["source_id"],
                    source_url="env:OLD_PROJECT_DIR",
                    download_url=f"local-copy:{source_ref}",
                    resolved_url=source_ref,
                    local_path=destination,
                    version_detected="old_project_snapshot",
                    license_or_citation="Local old project untrained data snapshot; reference only.",
                )
            )
            copied += 1
    if copied == 0 and not dry_run:
        append_manifest(
            manifest_failure(
                source_id=record["source_id"],
                source_url="env:OLD_PROJECT_DIR",
                failure_reason="No old project untrained data files were copied.",
                license_or_citation="Local old project untrained data snapshot; reference only.",
            )
        )
