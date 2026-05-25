from __future__ import annotations

import logging
from pathlib import Path

from .paths import LOG_DIR, ensure_project_dirs


def setup_logging(name: str = "arctic_doc_data_audit", level: int = logging.INFO) -> logging.Logger:
    ensure_project_dirs()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_path = Path(LOG_DIR) / f"{name}.log"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

