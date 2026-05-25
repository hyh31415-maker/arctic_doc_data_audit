from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def path(*parts: str | Path) -> Path:
    return project_root().joinpath(*map(Path, parts))


CONFIG_DIR = path("configs")
DATA_DIR = path("data")
RAW_DIR = path("data", "raw")
RAW_EXTERNAL_DIR = path("data", "raw_external")
INTERIM_DIR = path("data", "interim")
PROCESSED_DIR = path("data", "processed")
MANIFEST_DIR = path("data", "manifests")
OUTPUT_DIR = path("outputs")
REPORT_DIR = path("outputs", "reports")
TABLE_DIR = path("outputs", "tables")
LOG_DIR = path("outputs", "logs")


PROJECT_DIRS = [
    CONFIG_DIR,
    RAW_DIR,
    RAW_EXTERNAL_DIR,
    INTERIM_DIR,
    PROCESSED_DIR,
    MANIFEST_DIR,
    REPORT_DIR,
    TABLE_DIR,
    LOG_DIR,
]


def ensure_project_dirs() -> None:
    for directory in PROJECT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def relpath(value: str | Path) -> str:
    value_path = Path(value)
    try:
        return value_path.resolve().relative_to(project_root().resolve()).as_posix()
    except ValueError:
        return value_path.as_posix()

