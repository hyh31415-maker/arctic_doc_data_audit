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


def model_readiness() -> None:
    from .model_readiness import generate_model_readiness_report

    generate_model_readiness_report()


def complete_data_sources(args: argparse.Namespace) -> None:
    from .data_completion import complete_data_sources as run_completion

    run_completion(all_sources=args.all)


def audit_candidate_labels(args: argparse.Namespace) -> None:
    from .data_completion import audit_candidate_labels as run_audit

    run_audit(promote_approved=args.promote_approved)


def freeze_data(args: argparse.Namespace) -> None:
    from .data_completion import freeze_data as run_freeze

    run_freeze(args.freeze_id, run_tests=True)


def qa_data() -> None:
    from .data_qa import qa_data as run_qa

    run_qa()


def fix_gee_failures(args: argparse.Namespace) -> None:
    from .data_qa import fix_gee_failures as run_fix

    run_fix(all_sources=args.all)


def discover_wqp_characteristics() -> None:
    from .data_completion import discover_wqp_characteristics as run_discovery

    run_discovery()


def gee_auth_check() -> None:
    from .gee_regeneration import gee_auth_check as run_check

    run_check()


def run_gee_extraction(args: argparse.Namespace) -> None:
    from .gee_regeneration import run_all_gee_extractions, run_gee_extraction as run_one

    if args.all:
        run_all_gee_extractions(roi_set=args.roi_set)
    else:
        run_one(args.source, args.rivers, args.years, args.roi_set)


def complete_basin_context() -> None:
    from .data_completion import complete_basin_context as run_complete_basin_context

    run_complete_basin_context()


def finalize_candidate_sources(args: argparse.Namespace) -> None:
    from .data_completion import finalize_candidate_sources as run_finalize

    run_finalize(defer_datastream=args.defer_datastream)


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
    subparsers.add_parser("model-readiness", help="Audit whether canonical data are ready for future model training without training a model.")
    complete = subparsers.add_parser("complete-data-sources", help="Complete candidate source queries and data-freeze prerequisites without model training.")
    complete.add_argument("--all", action="store_true", help="Run every data-completion source audit/query.")
    candidate_audit = subparsers.add_parser("audit-candidate-labels", help="Audit candidate external labels and duplicate decisions without default promotion.")
    candidate_audit.add_argument("--promote-approved", action="store_true", help="Promote only explicitly approved candidates; default is no promotion.")
    freeze = subparsers.add_parser("freeze-data", help="Create data freeze reports and hashes without training a model.")
    freeze.add_argument("--freeze-id", required=True, help="Freeze identifier, e.g. data_freeze_YYYYMMDD_v1.")
    subparsers.add_parser("qa-data", help="Run data QA audits and source-priority checks without model training.")
    fix_gee = subparsers.add_parser("fix-gee-failures", help="Fix or supersede current GEE failures without model training.")
    fix_gee.add_argument("--all", action="store_true", help="Audit and fix all GEE sources.")
    subparsers.add_parser("discover-wqp-characteristics", help="Discover actual WQP CharacteristicName values and rebuild candidate QC.")
    subparsers.add_parser("rebuild-training-matrix-v3", help="Rebuild training matrix and v3 source-audit sidecars without model training.")
    subparsers.add_parser("gee-auth-check", help="Check Earth Engine authentication without printing credentials.")
    gee = subparsers.add_parser("run-gee-extraction", help="Run regenerated GEE extraction without model training.")
    gee.add_argument("--all", action="store_true", help="Run all configured GEE regenerated extraction sources.")
    gee.add_argument("--source", default="hls", choices=["hls", "sentinel2", "landsat_c2", "era5_land", "modis_snow", "smap"], help="Single GEE source to extract.")
    gee.add_argument("--rivers", default="all", help="Comma-separated rivers or all.")
    gee.add_argument("--years", default="", help="Year range such as 2016-2025.")
    gee.add_argument("--roi-set", default="final_primary", help="ROI set to use.")
    subparsers.add_parser("complete-basin-context", help="Complete or explicitly approximate basin context status.")
    finalize = subparsers.add_parser("finalize-candidate-sources", help="Finalize candidate source status without promotion or model training.")
    finalize.add_argument("--defer-datastream", action="store_true", help="Mark DataStream as deferred by user and not blocking full training.")
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
    elif args.command == "model-readiness":
        model_readiness()
        logger.info("Model readiness report generated without model training.")
    elif args.command == "complete-data-sources":
        complete_data_sources(args)
        logger.info("Data source completion finished without model training.")
    elif args.command == "audit-candidate-labels":
        audit_candidate_labels(args)
        logger.info("Candidate label audit finished without default promotion or model training.")
    elif args.command == "freeze-data":
        freeze_data(args)
        logger.info("Data freeze report generated without model training.")
    elif args.command == "qa-data":
        qa_data()
        logger.info("Data QA report generated without model training.")
    elif args.command == "fix-gee-failures":
        fix_gee_failures(args)
        build_training_matrix()
        model_readiness()
        logger.info("GEE failure QA/fix step completed without model training.")
    elif args.command == "discover-wqp-characteristics":
        discover_wqp_characteristics()
        generate_reports()
        logger.info("WQP characteristic discovery completed without candidate promotion or model training.")
    elif args.command == "rebuild-training-matrix-v3":
        build_training_matrix()
        model_readiness()
        logger.info("Training matrix v3 rebuilt without model training.")
    elif args.command == "gee-auth-check":
        gee_auth_check()
        logger.info("GEE auth check completed without model training.")
    elif args.command == "run-gee-extraction":
        run_gee_extraction(args)
        build_training_matrix()
        model_readiness()
        logger.info("GEE regenerated extraction completed without model training.")
    elif args.command == "complete-basin-context":
        complete_basin_context()
        generate_reports()
        logger.info("Basin context completion finished without model training.")
    elif args.command == "finalize-candidate-sources":
        finalize_candidate_sources(args)
        generate_reports()
        logger.info("Candidate sources finalized without model training.")
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
