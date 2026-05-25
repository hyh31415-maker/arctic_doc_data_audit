from __future__ import annotations

import requests

from ..manifest import append_manifest, manifest_failure, manifest_for_file, source_by_id
from ..paths import path


def acquire_arctic_data_center(dry_run: bool = True) -> None:
    record = source_by_id("arctic_data_center_tank_2023")
    doi_url = record["source_url"]
    destination = path(record.get("local_subdir", "data/raw_external/arctic_data_center/tank_2023")) / "doi_landing_page.html"
    if dry_run:
        append_manifest(
            {
                "source_id": record["source_id"],
                "source_url": doi_url,
                "resolved_url": "",
                "download_url": doi_url,
                "retrieved_at_utc": "",
                "local_path": str(destination),
                "file_name": destination.name,
                "file_size_bytes": "",
                "sha256": "",
                "version_detected": record.get("doi", ""),
                "download_status": "dry_run",
                "failure_reason": "Dry-run only. Resolve DOI and review package members before bulk download.",
                "license_or_citation": f"DOI {record.get('doi', '')}",
                "commit_raw_data": False,
            }
        )
        return
    try:
        response = requests.get(doi_url, timeout=60, allow_redirects=True)
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(response.text, encoding="utf-8", errors="replace")
        append_manifest(
            manifest_for_file(
                source_id=record["source_id"],
                source_url=doi_url,
                download_url=doi_url,
                resolved_url=response.url,
                local_path=destination,
                version_detected=record.get("doi", ""),
                license_or_citation=f"DOI {record.get('doi', '')}; benchmark/fixed-version validation source.",
            )
        )
    except Exception as exc:
        append_manifest(
            manifest_failure(
                source_id=record["source_id"],
                source_url=doi_url,
                download_url=doi_url,
                failure_reason=str(exc),
                local_path=destination,
                version_detected=record.get("doi", ""),
                license_or_citation=f"DOI {record.get('doi', '')}",
            )
        )

