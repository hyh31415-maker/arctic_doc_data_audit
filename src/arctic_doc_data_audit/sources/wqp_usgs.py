from __future__ import annotations

from urllib.parse import urlencode

import requests

from ..manifest import append_manifest, manifest_failure, manifest_for_file, source_by_id
from ..paths import path


def _result_query_url(characteristics: list[str]) -> str:
    params = {
        "countrycode": "US",
        "statecode": "US:02",
        "siteType": "Stream",
        "bBox": "-164.2,61.2,-161.4,62.6",
        "mimeType": "csv",
        "zip": "no",
    }
    query = urlencode(params)
    chars = "&".join(f"characteristicName={requests.utils.quote(value)}" for value in characteristics)
    return f"https://www.waterqualitydata.us/data/Result/search?{query}&{chars}"


def download_wqp_yukon_candidates(dry_run: bool = True) -> None:
    record = source_by_id("wqp_usgs_yukon_candidate")
    characteristics = list(record.get("characteristics", []))
    query_url = _result_query_url(characteristics)
    destination = path(record.get("local_subdir", "data/raw_external/wqp_usgs")) / "yukon_candidate_results.csv"
    if dry_run:
        append_manifest(
            {
                "source_id": record["source_id"],
                "source_url": record["source_url"],
                "resolved_url": "",
                "download_url": query_url,
                "retrieved_at_utc": "",
                "local_path": str(destination),
                "file_name": destination.name,
                "file_size_bytes": "",
                "sha256": "",
                "version_detected": "live_service_query",
                "download_status": "dry_run",
                "failure_reason": "Candidate query only; results need label QC before use.",
                "license_or_citation": "Water Quality Portal / USGS candidate data.",
                "commit_raw_data": False,
            }
        )
        return
    try:
        response = requests.get(query_url, timeout=120)
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        append_manifest(
            manifest_for_file(
                source_id=record["source_id"],
                source_url=record["source_url"],
                download_url=query_url,
                resolved_url=response.url,
                local_path=destination,
                version_detected="live_service_query",
                license_or_citation="Water Quality Portal / USGS candidate data.",
            )
        )
    except Exception as exc:
        append_manifest(
            manifest_failure(
                source_id=record["source_id"],
                source_url=record["source_url"],
                download_url=query_url,
                failure_reason=str(exc),
                local_path=destination,
                version_detected="live_service_query",
                license_or_citation="Water Quality Portal / USGS candidate data.",
            )
        )

