from __future__ import annotations

from ..manifest import append_manifest, source_by_id
from ..paths import path


def download_datastream_mackenzie_candidates(dry_run: bool = True) -> None:
    record = source_by_id("datastream_mackenzie_candidate")
    destination = path(record.get("local_subdir", "data/raw_external/datastream_mackenzie")) / "candidate_query_instructions.md"
    status = "dry_run" if dry_run else "manual_required"
    append_manifest(
        {
            "source_id": record["source_id"],
            "source_url": record["source_url"],
            "resolved_url": record["source_url"],
            "download_url": record["source_url"],
            "retrieved_at_utc": "",
            "local_path": str(destination),
            "file_name": destination.name,
            "file_size_bytes": "",
            "sha256": "",
            "version_detected": "live_api",
            "download_status": status,
            "failure_reason": "Use DataStream API/hub search for Mackenzie DOC/TOC/CDOM/UV/turbidity candidates; keep candidate-only QC.",
            "license_or_citation": "DataStream candidate metadata; verify API terms before redistribution.",
            "commit_raw_data": False,
        }
    )
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "# DataStream Mackenzie Candidate Acquisition\n\n"
            "Search the Mackenzie hub for DOC, TOC, CDOM, UV absorbance, turbidity, and related water-quality observations. "
            "Retain site metadata and classify every row through candidate-label QC before any training use.\n",
            encoding="utf-8",
        )

