from __future__ import annotations

from ..manifest import append_manifest, source_by_id
from ..paths import path


def acquire_partners_mdpi_candidates(dry_run: bool = True) -> None:
    record = source_by_id("partners_mdpi_eurasian_candidate")
    destination = path(record.get("local_subdir", "data/raw_external/partners_mdpi")) / "acquisition_instructions.md"
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
            "version_detected": "publication_supplement",
            "download_status": "dry_run" if dry_run else "manual_required",
            "failure_reason": "Search/download supplementary tables conservatively and preserve article/source citation before parsing.",
            "license_or_citation": "Publication supplementary data; citation required.",
            "commit_raw_data": False,
        }
    )
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "# PARTNERS / MDPI Eurasian Candidate Acquisition\n\n"
            "Locate supplementary DOC and chemistry tables for Ob, Yenisey, Lena, and Kolyma. "
            "Do not merge until duplicate/provenance audit is complete.\n",
            encoding="utf-8",
        )

