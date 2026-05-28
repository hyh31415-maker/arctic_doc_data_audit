from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from .manifest import sha256_file
from .paths import path, relpath


FREEZE_ID_DEFAULT = "data_freeze_gold_20260526_v1"
GOLD_DIR = path("data", "processed", "gold")
GOLD_REPORT_DIR = path("outputs", "reports", "gold")
GOLD_TABLE_DIR = path("outputs", "tables", "gold")
ARCHIVE_REPORT = GOLD_REPORT_DIR / "gold_freeze_archive_report.md"
ARCHIVE_MANIFEST = GOLD_TABLE_DIR / "gold_freeze_archive_manifest.csv"
TRACKED_ARTIFACT_AUDIT = GOLD_TABLE_DIR / "tracked_model_artifact_audit.csv"
HANDOFF_REPORT = GOLD_REPORT_DIR / "frozen_repository_handoff.md"
ARTIFACT_PATTERN = re.compile(r"model|prediction|predicted|flux|joblib|pkl|pickle", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=path(), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _git_success(args: list[str]) -> bool:
    try:
        subprocess.check_call(["git", *args], cwd=path(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _tracked_paths() -> set[str]:
    output = _git_output(["ls-files"])
    return {line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()}


def _remote_tag_exists(freeze_id: str) -> bool:
    return bool(_git_output(["ls-remote", "--tags", "origin", freeze_id]))


def _release_status(freeze_id: str) -> str:
    try:
        result = subprocess.run(
            ["gh", "release", "view", freeze_id, "--json", "tagName,url,isDraft,isPrerelease,publishedAt"],
            cwd=path(),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except Exception:
        return "unknown (gh unavailable)"
    if result.returncode == 0:
        return result.stdout.strip()
    message = (result.stderr or result.stdout).strip()
    return message or "not found"


def _iter_files(items: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for item in items:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(child for child in item.rglob("*") if child.is_file())
    return sorted(files, key=lambda item: relpath(item))


def _archive_group(file_path: Path) -> str:
    relative = relpath(file_path)
    name = file_path.name.lower()
    if relative.startswith("data/processed/gold/"):
        return "gold_table"
    if relative.startswith("outputs/reports/gold/"):
        return "gold_report"
    if "hash" in name:
        return "gold_table_hash"
    if "manifest" in name or relative.startswith("data/manifests/"):
        return "manifest"
    if relative.startswith("configs/"):
        return "config"
    if relative == "README.md":
        return "readme"
    if relative == "pyproject.toml":
        return "code_reference"
    if relative.startswith("outputs/tables/gold/"):
        return "gold_report"
    return "code_reference"


def _backup_exists(freeze_id: str, relative: str) -> bool:
    return path("backups", freeze_id, *relative.split("/")).exists()


def _notes(group: str, relative: str, included_in_git: bool, included_in_backup: bool) -> str:
    notes: list[str] = []
    if group == "gold_table" and not included_in_git:
        notes.append("gold CSV remains local and gitignored")
    if relative.startswith("configs/local_paths."):
        notes.append("local-only configuration path")
    if relative in {
        "outputs/tables/gold/hydroclimate_legacy_vs_regenerated_used.csv",
        "outputs/tables/gold/hydroclimate_source_resolution.csv",
    }:
        notes.append("large row-level audit sidecar kept out of git")
    if not included_in_backup:
        notes.append("missing from local backup")
    return "; ".join(notes)


def _scan_archive_files(freeze_id: str) -> list[dict[str, object]]:
    tracked = _tracked_paths()
    targets = [
        GOLD_DIR,
        GOLD_REPORT_DIR,
        GOLD_TABLE_DIR,
        path("README.md"),
        path("pyproject.toml"),
        path("configs"),
        path("data", "manifests"),
    ]
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for file_path in _iter_files(targets):
        relative = relpath(file_path)
        if relative in seen or relative == relpath(ARCHIVE_MANIFEST):
            continue
        seen.add(relative)
        group = _archive_group(file_path)
        included_in_git = relative in tracked
        included_in_backup = _backup_exists(freeze_id, relative)
        rows.append(
            {
                "freeze_id": freeze_id,
                "file_path": str(file_path),
                "relative_path": relative,
                "file_size_bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
                "archive_group": group,
                "included_in_git": included_in_git,
                "included_in_local_backup": included_in_backup,
                "notes": _notes(group, relative, included_in_git, included_in_backup),
            }
        )
    return sorted(rows, key=lambda row: str(row["relative_path"]))


def _artifact_type(relative: str) -> str:
    lower = relative.lower()
    if lower.startswith("outputs/models/") or lower.endswith((".joblib", ".pkl", ".pickle")):
        return "model_binary_or_model_output"
    if lower.startswith("outputs/predictions/") or "prediction" in lower or "predicted" in lower:
        return "prediction_reference"
    if lower.startswith("outputs/flux/") or "flux" in lower:
        return "flux_reference"
    if "model_input_table_hashes.csv" in lower:
        return "gold_hash_manifest"
    if lower.endswith(".py"):
        return "code_reference"
    if lower.endswith(".md") or lower.startswith("outputs/reports/"):
        return "documentation"
    return "metadata_reference"


def write_tracked_model_artifact_audit() -> tuple[Path, list[dict[str, object]]]:
    TRACKED_ARTIFACT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for relative in sorted(_tracked_paths()):
        if not ARTIFACT_PATTERN.search(relative):
            continue
        lower = relative.lower()
        is_output = (
            lower.startswith(("outputs/models/", "outputs/predictions/", "outputs/flux/"))
            or lower.endswith((".joblib", ".pkl", ".pickle"))
            or lower.endswith("_flux.csv")
            or "doc_prediction" in lower
        )
        is_documentation = lower.endswith(".md") or lower.startswith("outputs/reports/")
        artifact_type = _artifact_type(relative)
        rows.append(
            {
                "file_path": relative,
                "artifact_type": artifact_type,
                "is_documentation": is_documentation,
                "is_model_output": is_output,
                "recommended_action": "review and remove from git" if is_output else "retain",
                "action_taken": "reported_only" if is_output else "retained",
                "notes": "no model/prediction/flux output detected" if not is_output else "tracked generated artifact candidate",
            }
        )
    frame = pd.DataFrame(
        rows,
        columns=[
            "file_path",
            "artifact_type",
            "is_documentation",
            "is_model_output",
            "recommended_action",
            "action_taken",
            "notes",
        ],
    )
    frame.to_csv(TRACKED_ARTIFACT_AUDIT, index=False, encoding="utf-8")
    return TRACKED_ARTIFACT_AUDIT, rows


def write_handoff_report(freeze_id: str) -> Path:
    HANDOFF_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Frozen Repository Handoff",
        "",
        f"- freeze_id: `{freeze_id}`",
        f"- tag_name: `{freeze_id}`",
        "- repository_role: Frozen Data Repository",
        "- gold_tables_location: `data/processed/gold/`",
        f"- local_backup_location: `backups/{freeze_id}/`",
        "- hash_manifest_location: `outputs/tables/gold/gold_freeze_archive_manifest.csv`",
        "- original_gold_table_hashes: `outputs/tables/gold/gold_table_hashes.csv`",
        "- fatal_data_bug_policy: `outputs/reports/gold/fatal_data_bug_policy.md`",
        "",
        "## Future Modeling Repository Recommendation",
        "",
        "Create a clean modeling repository that treats this repository as a frozen data source. Future modeling code should read only `data/processed/gold/*` from this freeze and should keep model outputs outside this data repository.",
        "",
        "## What Not To Modify",
        "",
        "- Do not use raw/interim/canonical tables directly in modeling.",
        "- Do not use old project snapshot directly.",
        "- Do not modify gold tables during modeling.",
        "- Do not train DOC models in this repository.",
        "- Do not generate DOC prediction or flux products in this repository.",
        "- If a fatal data bug is found, create a new freeze version instead of silently editing this freeze.",
        "",
        "## How To Verify Local Gold Tables",
        "",
        "```powershell",
        f"python -m arctic_doc_data_audit.cli archive-gold-freeze --freeze-id {freeze_id}",
        "python -m pytest tests/test_gold_freeze.py",
        "```",
        "",
        "The archive manifest records SHA256 values for the local gold CSVs. The gold CSV files remain local processed artifacts and are not committed to Git.",
    ]
    HANDOFF_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return HANDOFF_REPORT


def _write_archive_report(freeze_id: str, rows: list[dict[str, object]], artifact_rows: list[dict[str, object]]) -> Path:
    ARCHIVE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    branch = _git_output(["branch", "--show-current"]) or "unknown"
    commit = _git_output(["rev-parse", "HEAD"]) or "unknown"
    tag_exists = _git_success(["rev-parse", "--verify", f"refs/tags/{freeze_id}"])
    remote_tag = _remote_tag_exists(freeze_id)
    release_status = _release_status(freeze_id)
    gold_tables = [row for row in rows if row["archive_group"] == "gold_table"]
    gold_reports = [row for row in rows if row["archive_group"] == "gold_report"]
    missing_backup = [row for row in rows if not bool(row["included_in_local_backup"])]
    tracked_outputs = [row for row in artifact_rows if bool(row["is_model_output"])]
    lines = [
        "# Gold Freeze Archive Report",
        "",
        f"Generated: {utc_now()}",
        "",
        f"- freeze_id: `{freeze_id}`",
        f"- git_branch: `{branch}`",
        f"- git_commit: `{commit}`",
        f"- local_tag_exists: `{tag_exists}`",
        f"- remote_tag_exists: `{remote_tag}`",
        f"- github_release_status: `{release_status}`",
        f"- local_backup_location: `backups/{freeze_id}/`",
        "- archive_manifest: `outputs/tables/gold/gold_freeze_archive_manifest.csv`",
        "- tracked_model_artifact_audit: `outputs/tables/gold/tracked_model_artifact_audit.csv`",
        "",
        "## Verification Summary",
        "",
        f"- gold_table_files_hashed: `{len(gold_tables)}`",
        f"- gold_report_or_audit_files_hashed: `{len(gold_reports)}`",
        f"- manifest_rows: `{len(rows)}`",
        f"- files_missing_from_local_backup: `{len(missing_backup)}`",
        f"- tracked_model_outputs_found: `{len(tracked_outputs)}`",
        "",
        "No DOC model was trained in this repository. No DOC prediction was generated. No flux product was generated.",
        "",
        "## GitHub Seal Status",
        "",
        f"The local and remote Git tag `{freeze_id}` are recorded above. No GitHub release was created by this archive command.",
        "",
        "## Local Backup Scope",
        "",
        "The local backup is expected to include `data/processed/gold/`, `outputs/reports/gold/`, `outputs/tables/gold/`, `README.md`, `pyproject.toml`, `configs/`, and `data/manifests/`.",
    ]
    if missing_backup:
        lines.extend(["", "## Backup Gaps", ""])
        for row in missing_backup[:50]:
            lines.append(f"- `{row['relative_path']}`")
    ARCHIVE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ARCHIVE_REPORT


def archive_gold_freeze(freeze_id: str = FREEZE_ID_DEFAULT) -> tuple[Path, Path]:
    if not GOLD_DIR.exists() or not any(GOLD_DIR.glob("*.csv")):
        raise SystemExit("Missing data/processed/gold/*.csv; cannot archive gold freeze for future modeling.")

    GOLD_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    _, artifact_rows = write_tracked_model_artifact_audit()
    write_handoff_report(freeze_id)
    preliminary_rows = _scan_archive_files(freeze_id)
    report_path = _write_archive_report(freeze_id, preliminary_rows, artifact_rows)
    rows = _scan_archive_files(freeze_id)
    frame = pd.DataFrame(
        rows,
        columns=[
            "freeze_id",
            "file_path",
            "relative_path",
            "file_size_bytes",
            "sha256",
            "archive_group",
            "included_in_git",
            "included_in_local_backup",
            "notes",
        ],
    )
    frame.to_csv(ARCHIVE_MANIFEST, index=False, encoding="utf-8")
    return report_path, ARCHIVE_MANIFEST
