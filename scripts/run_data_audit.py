from __future__ import annotations

from arctic_doc_data_audit.cli import build_training_matrix, init_project, preprocess_all
from arctic_doc_data_audit.reports import generate_reports
from arctic_doc_data_audit.sources.arcticgro import download_arcticgro


def main() -> None:
    init_project()
    download_arcticgro(dry_run=False)
    preprocess_all()
    build_training_matrix()
    generate_reports()


if __name__ == "__main__":
    main()

