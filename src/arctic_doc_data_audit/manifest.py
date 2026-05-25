from __future__ import annotations

import hashlib
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .paths import CONFIG_DIR, MANIFEST_DIR, ensure_project_dirs, relpath
from .schemas import ensure_columns, required_columns


SOURCE_REGISTRY_PATH = MANIFEST_DIR / "source_registry.csv"
FILE_MANIFEST_PATH = MANIFEST_DIR / "file_manifest.csv"
FILE_MANIFEST_LOCK = MANIFEST_DIR / "file_manifest.lock"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_sources_config() -> dict[str, Any]:
    with (CONFIG_DIR / "sources.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def source_records() -> list[dict[str, Any]]:
    return list(load_sources_config().get("sources", []))


def source_by_id(source_id: str) -> dict[str, Any]:
    for record in source_records():
        if record["source_id"] == source_id:
            return record
    raise KeyError(f"Unknown source_id: {source_id}")


def write_source_registry() -> Path:
    ensure_project_dirs()
    rows = []
    for record in source_records():
        rows.append(
            {
                "source_id": record.get("source_id", ""),
                "source_family": record.get("source_family", ""),
                "data_role": record.get("data_role", ""),
                "source_url": record.get("source_url", ""),
                "official_or_secondary": record.get("official_or_secondary", ""),
                "expected_update_frequency": record.get("expected_update_frequency", ""),
                "version_policy": record.get("version_policy", ""),
                "raw_commit_allowed": bool(record.get("raw_commit_allowed", False)),
                "notes": record.get("notes", ""),
            }
        )
    frame = ensure_columns(pd.DataFrame(rows), "source_registry")
    frame.to_csv(SOURCE_REGISTRY_PATH, index=False, encoding="utf-8")
    return SOURCE_REGISTRY_PATH


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest() -> pd.DataFrame:
    ensure_project_dirs()
    if FILE_MANIFEST_PATH.exists():
        try:
            frame = pd.read_csv(FILE_MANIFEST_PATH, dtype=str).fillna("")
        except pd.errors.EmptyDataError:
            frame = pd.DataFrame(columns=required_columns("file_manifest"))
    else:
        frame = pd.DataFrame(columns=required_columns("file_manifest"))
    return ensure_columns(frame, "file_manifest")


def write_manifest(frame: pd.DataFrame) -> Path:
    ensure_project_dirs()
    frame = ensure_columns(frame, "file_manifest")
    tmp_path = FILE_MANIFEST_PATH.with_suffix(".csv.tmp")
    frame.to_csv(tmp_path, index=False, encoding="utf-8")
    tmp_path.replace(FILE_MANIFEST_PATH)
    return FILE_MANIFEST_PATH


@contextmanager
def manifest_lock(timeout_seconds: float = 60.0):
    ensure_project_dirs()
    start = time.time()
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(FILE_MANIFEST_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
        except FileExistsError:
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Timed out waiting for manifest lock: {FILE_MANIFEST_LOCK}")
            time.sleep(0.1)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            FILE_MANIFEST_LOCK.unlink()
        except FileNotFoundError:
            pass


def append_manifest(row: dict[str, Any]) -> Path:
    with manifest_lock():
        frame = read_manifest()
        normalized = {column: row.get(column, "") for column in required_columns("file_manifest")}
        if normalized.get("retrieved_at_utc") in ("", None):
            normalized["retrieved_at_utc"] = utc_now()
        if "commit_raw_data" not in normalized or normalized["commit_raw_data"] in ("", None):
            normalized["commit_raw_data"] = False
        if normalized.get("local_path"):
            normalized["local_path"] = relpath(normalized["local_path"])
        frame = pd.concat([frame, pd.DataFrame([normalized])], ignore_index=True)
        subset = ["source_id", "local_path", "download_url"]
        frame = frame.drop_duplicates(subset=subset, keep="last")
        return write_manifest(frame)


@dataclass(frozen=True)
class DownloadResult:
    source_id: str
    source_url: str
    resolved_url: str
    download_url: str
    local_path: str
    file_name: str
    file_size_bytes: int | str
    sha256: str
    version_detected: str
    download_status: str
    failure_reason: str
    license_or_citation: str
    commit_raw_data: bool = False

    def as_manifest_row(self) -> dict[str, Any]:
        row = self.__dict__.copy()
        row["retrieved_at_utc"] = utc_now()
        return row


def manifest_for_file(
    *,
    source_id: str,
    source_url: str,
    download_url: str,
    resolved_url: str,
    local_path: str | Path,
    version_detected: str = "",
    license_or_citation: str = "",
    status: str = "downloaded",
) -> dict[str, Any]:
    local = Path(local_path)
    return DownloadResult(
        source_id=source_id,
        source_url=source_url,
        resolved_url=resolved_url,
        download_url=download_url,
        local_path=relpath(local),
        file_name=local.name,
        file_size_bytes=local.stat().st_size if local.exists() else "",
        sha256=sha256_file(local) if local.exists() and local.is_file() else "",
        version_detected=version_detected,
        download_status=status,
        failure_reason="",
        license_or_citation=license_or_citation,
        commit_raw_data=False,
    ).as_manifest_row()


def manifest_failure(
    *,
    source_id: str,
    source_url: str,
    download_url: str = "",
    resolved_url: str = "",
    failure_reason: str,
    version_detected: str = "",
    license_or_citation: str = "",
    local_path: str | Path = "",
) -> dict[str, Any]:
    local_text = relpath(local_path) if local_path else ""
    return {
        "source_id": source_id,
        "source_url": source_url,
        "resolved_url": resolved_url,
        "download_url": download_url,
        "retrieved_at_utc": utc_now(),
        "local_path": local_text,
        "file_name": Path(local_text).name if local_text else "",
        "file_size_bytes": "",
        "sha256": "",
        "version_detected": version_detected,
        "download_status": "failed",
        "failure_reason": failure_reason,
        "license_or_citation": license_or_citation,
        "commit_raw_data": False,
    }
