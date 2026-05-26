from __future__ import annotations

import argparse
from typing import Iterable

from .logging_utils import setup_logging
from .manifest import write_source_registry
from .paths import ensure_project_dirs
from .reports import generate_reports
from .schemas import empty_table, write_table
from .sources.arctic_data_center import acquire_arctic_data_center
from .sources.arcticgro import download_arcticgro
from .sources.datastream import download_datastream_mackenzie_candidates
from .sources.gee_hydroclimate import gee_hydroclimate_dry_run
from .sources.gee_optical import gee_optical_dry_run
from .sources.hydrobasins import acquire_hydrosheds_context
from .sources.old_project import import_old_project_reference, import_old_project_untrained_data
from .sources.partners_mdpi import acquire_partners_mdpi_candidates
from .sources.wqp_usgs import download_wqp_yukon_candidates


def init_project() -> None:
    ensure_project_dirs()
    write_source_registry()
    for table_name in [
        "doc_labels_raw",
        "doc_labels_canonical",
        "lab_optical_proxy_canonical",
        "daily_discharge_canonical",
        "daily_hydroclimate_canonical",
        "roi_catalog",
        "optical_timeseries_canonical",
        "basin_context_canonical",
        "auxiliary_context_canonical",
        "training_matrix_daily_predictable",
    ]:
        write_table(empty_table(table_name), table_name)


def preprocess_all() -> None:
    from .preprocess import absorbance, basin_context, candidate_labels, discharge, doc_labels, hydroclimate, optical_timeseries

    doc_labels.run()
    absorbance.run()
    discharge.run()
    candidate_labels.run()
    hydroclimate.run()
    optical_timeseries.run()
    basin_context.run()


def build_training_matrix() -> None:
    from .preprocess import training_matrix

    training_matrix.run()


def audit_old_snapshot() -> None:
    from .preprocess import old_snapshot

    old_snapshot.audit_old_snapshot()


def promote_old_snapshot(args: argparse.Namespace) -> None:
    from .preprocess import old_snapshot

    if args.all:
        families = ["raw_compare", "roi", "hydroclimate", "optical", "auxiliary"]
    else:
        families = [item.strip() for item in (args.families or "").split(",") if item.strip()]
    if not families:
        raise SystemExit("Specify --families roi,hydroclimate,optical,auxiliary,raw_compare or --all.")
    old_snapshot.promote_old_snapshot(families)


def run_download(args: argparse.Namespace) -> None:
    source = args.source.lower()
    if source in {"arcticgro", "all"}:
        download_arcticgro(dry_run=args.dry_run)
    if source in {"old_project", "old_arctic_doc_snowmelt_outputs", "all"}:
        import_old_project_reference(dry_run=args.dry_run)
    if source in {"old_project_raw", "old_project_data", "old_arctic_doc_snowmelt_untrained_data", "all"}:
        import_old_project_untrained_data(dry_run=args.dry_run)
    if source in {"wqp_usgs", "wqp", "wqp_usgs_yukon_candidate", "all"}:
        download_wqp_yukon_candidates(dry_run=args.dry_run)
    if source in {"datastream", "datastream_mackenzie_candidate", "all"}:
        download_datastream_mackenzie_candidates(dry_run=args.dry_run)
    if source in {"arctic_data_center", "arctic_data_center_tank_2023", "all"}:
        acquire_arctic_data_center(dry_run=args.dry_run)
    if source in {"partners_mdpi", "partners", "partners_mdpi_eurasian_candidate", "all"}:
        acquire_partners_mdpi_candidates(dry_run=args.dry_run)
    if source in {"gee", "gee_optical", "all"}:
        gee_optical_dry_run(rivers=args.rivers, years=args.years, roi_set=args.roi_set, report_only=args.report_only or args.dry_run)
    if source in {"gee", "gee_hydroclimate", "all"}:
        gee_hydroclimate_dry_run(rivers=args.rivers, years=args.years, roi_set=args.roi_set, report_only=args.report_only or args.dry_run)
    if source in {"hydrobasins", "hydroatlas", "hydrosheds", "all"}:
        acquire_hydrosheds_context(dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arctic_doc_data_audit", description="Data acquisition and preprocessing audit for Arctic river DOC workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create project directories and empty canonical tables.")

    download = subparsers.add_parser("download", help="Download or record acquisition status for configured sources.")
    download.add_argument("--source", required=True, help="Source alias: arcticgro, wqp_usgs, datastream, arctic_data_center, partners_mdpi, gee_optical, gee_hydroclimate, hydrobasins, old_project, all.")
    download.add_argument("--dry-run", action="store_true", help="Record intended downloads without fetching raw data.")
    download.add_argument("--rivers", default="all", help="GEE dry-run river selector.")
    download.add_argument("--years", default="", help="GEE dry-run year selector, e.g. 2017-2025.")
    download.add_argument("--roi-set", default="default", help="GEE dry-run ROI set name.")
    download.add_argument("--chunk-by-year", action="store_true", help="Record chunk-by-year preference for GEE dry runs.")
    download.add_argument("--resume", action="store_true", help="Record resume preference for GEE dry runs.")
    download.add_argument("--report-only", action="store_true", help="Record report-only GEE mode.")

    preprocess = subparsers.add_parser("preprocess", help="Build canonical tables from available local data.")
    preprocess.add_argument("--all", action="store_true", help="Run all preprocessors.")

    subparsers.add_parser("build-training-matrix", help="Build future daily-predictable training matrix without training a model.")
    subparsers.add_parser("audit-old-snapshot", help="Audit old project snapshot files and generate inventory/raw-compare tables.")
    promote = subparsers.add_parser("promote-old-snapshot", help="Promote audited old snapshot families into canonical tables.")
    promote.add_argument("--families", default="", help="Comma-separated families: roi,hydroclimate,optical,auxiliary,raw_compare.")
    promote.add_argument("--all", action="store_true", help="Promote all supported old snapshot families.")
    subparsers.add_parser("report", help="Generate data availability and provenance reports.")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    logger = setup_logging()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    ensure_project_dirs()
    write_source_registry()

    if args.command == "init":
        init_project()
        logger.info("Initialized project scaffold and empty canonical tables.")
    elif args.command == "download":
        run_download(args)
        generate_reports()
        logger.info("Download/acquisition step complete.")
    elif args.command == "preprocess":
        if args.all:
            preprocess_all()
        else:
            preprocess_all()
        generate_reports()
        logger.info("Preprocessing complete.")
    elif args.command == "build-training-matrix":
        build_training_matrix()
        generate_reports()
        logger.info("Training matrix built without model training.")
    elif args.command == "audit-old-snapshot":
        audit_old_snapshot()
        generate_reports()
        logger.info("Old snapshot audit complete.")
    elif args.command == "promote-old-snapshot":
        promote_old_snapshot(args)
        build_training_matrix()
        generate_reports()
        logger.info("Old snapshot promotion complete without model training.")
    elif args.command == "report":
        generate_reports()
        logger.info("Reports generated.")
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
