from __future__ import annotations

from pathlib import Path

from arctic_doc_data_audit.manifest import manifest_for_file


def test_manifest_downloaded_file_has_sha256_and_raw_not_committed(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")
    row = manifest_for_file(
        source_id="test_source",
        source_url="https://example.com",
        download_url="https://example.com/file",
        resolved_url="https://example.com/file",
        local_path=file_path,
    )
    assert len(row["sha256"]) == 64
    assert row["commit_raw_data"] is False

