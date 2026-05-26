# arctic_doc_data_audit

Clean data acquisition and preprocessing code for Arctic river DOC / CDOM / discharge / optical proxy / hydroclimate integration.

This repository is a data-layer rebuild only. It downloads, audits, standardizes, deduplicates, joins, and reports data readiness for later Arctic river DOC / snowmelt / flux modeling. It does not train DOC models and does not make final scientific claims.

## Data Roles

- DOC labels: field DOC observations suitable for future model labels after QC.
- TOC labels: retained separately and flagged with `is_toc_not_doc=true`; never silently converted to DOC.
- Daily predictors: discharge and hydroclimate variables that can be known or reconstructed as continuous daily predictors.
- Lab optical proxy: ArcticGRO absorbance/CDOM variables such as A254, A375, A440, SUVA, and spectral slopes.
- Satellite optical proxy: HLS, Sentinel-2, and Landsat reflectance-derived optical time series.
- Basin context: HydroBASINS/HydroATLAS attributes and local basin metadata.
- Benchmark products: fixed-version literature or data packages used for validation after duplicate/provenance audit.

Lab absorbance/CDOM is not included as a production daily flux-model predictor because it is sample-tied laboratory information, not a continuous daily variable available for every prediction date. It can support DOC-CDOM mechanism checks and satellite optical interpretation. Satellite reflectance is also an optical proxy, not a direct DOC observation.

## Quick Start

```powershell
python -m pip install -e .[test]
python -m arctic_doc_data_audit.cli init
python -m arctic_doc_data_audit.cli download --source arcticgro --dry-run
python -m arctic_doc_data_audit.cli download --source arcticgro
python -m arctic_doc_data_audit.cli preprocess --all
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli complete-data-sources --all
python -m arctic_doc_data_audit.cli audit-candidate-labels
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_YYYYMMDD_v1
python -m arctic_doc_data_audit.cli report
python -m pytest
```

Equivalent Make targets are available:

```powershell
make init
make download-arcticgro
make download-candidates
make preprocess
make build-matrix
make complete-data-sources
make audit-candidate-labels
make model-readiness
make freeze-data
make report
make test
```

## Outputs

- `data/manifests/source_registry.csv`
- `data/manifests/file_manifest.csv`
- `data/processed/doc_labels_raw.csv`
- `data/processed/doc_labels_canonical.csv`
- `data/processed/lab_optical_proxy_canonical.csv`
- `data/processed/daily_discharge_canonical.csv`
- `data/processed/daily_hydroclimate_canonical.csv`
- `data/processed/optical_timeseries_canonical.csv`
- `data/processed/basin_context_canonical.csv`
- `data/processed/training_matrix_daily_predictable.csv`
- `outputs/reports/data_availability_report.md`
- `outputs/reports/provenance_report.md`
- `outputs/reports/model_readiness_report.md`
- `outputs/reports/gee_extraction_readiness_report.md`
- `outputs/reports/data_freeze_report.md`

Raw, interim, and processed data directories are gitignored. Manifests and reports are lightweight audit artifacts and may be committed when they contain no sensitive local paths.

## Manual Data

For manual HydroBASINS/HydroATLAS or Arctic Data Center files, create `configs/local_paths.yaml`:

```yaml
hydrobasins:
  local_path: "D:/path/to/hydrobasins_file.geojson"
hydroatlas:
  local_path: "D:/path/to/hydroatlas_attributes.csv"
arctic_data_center_tank_2023:
  local_path: "D:/path/to/unpacked/package"
```

The file is gitignored. The parser records the local artifact in manifest/provenance but does not commit the data.

## Old Project Reference Import

Set `OLD_PROJECT_DIR` to a local checkout of the old project to copy selected non-raw reference tables into `data/interim/reference_old_project/`:

```powershell
$env:OLD_PROJECT_DIR="D:/Hao/Desktop/冰冻圈水文/北极大河DOC/arctic_doc_snowmelt"
python -m arctic_doc_data_audit.cli download --source old_project
```

Imported old files are reference-only. They are never treated as authoritative labels until regenerated from raw sources.

To copy old untrained source files as an isolated local snapshot, run:

```powershell
$env:OLD_PROJECT_DIR="D:/Hao/Desktop/冰冻圈水文/北极大河DOC/arctic_doc_snowmelt"
python -m arctic_doc_data_audit.cli download --source old_project_raw
```

This copies `data/raw`, `data/raw_external`, and `data/interim` into `data/raw_external/old_project_snapshot/`, records SHA256 rows in the manifest, and keeps the files out of git.

## Old Snapshot Audit and Promotion

The new project is the only main project. The old project directory is used only once to create a local snapshot; after that, future workflows should read this repository's canonical tables instead of old project code or paths.

```powershell
python -m arctic_doc_data_audit.cli download --source old_project_raw
python -m arctic_doc_data_audit.cli audit-old-snapshot
python -m arctic_doc_data_audit.cli promote-old-snapshot --all
python -m arctic_doc_data_audit.cli preprocess --all
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli report
```

`audit-old-snapshot` writes:

- `outputs/tables/old_snapshot_inventory.csv`
- `outputs/tables/old_snapshot_raw_compare.csv`
- `outputs/tables/discharge_candidate_station_inventory.csv`

`promote-old-snapshot --all` can promote legacy ROI, hydroclimate, HLS optical proxy, and auxiliary context rows into canonical tables with `source_id=old_arctic_doc_snowmelt_untrained_data`. Old model, prediction, and flux outputs are excluded. Old raw ArcticGRO files are compared to current official downloads and are not directly merged.

Legacy GEE/HLS/ERA5/MODIS rows are marked as legacy snapshot sources and can later be replaced by regenerated extraction from the new project.

## Future Training Inputs

Future modeling code should read `doc_labels_canonical.csv`, `daily_discharge_canonical.csv`, `daily_hydroclimate_canonical.csv`, `optical_timeseries_canonical.csv`, and `basin_context_canonical.csv`. The prepared `training_matrix_daily_predictable.csv` intentionally excludes lab absorbance/CDOM columns and is only a future input table, not a model result.

Before training, run:

```powershell
python -m arctic_doc_data_audit.cli complete-data-sources --all
python -m arctic_doc_data_audit.cli audit-candidate-labels
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_YYYYMMDD_v1
```

`complete-data-sources` queries or indexes remaining candidate sources, records failures/manual requirements in the manifest, and writes candidate QC tables without promotion. `audit-candidate-labels` produces a promotion plan only by default. `model-readiness` checks label counts, predictor completeness, optical match windows, season-window coverage, source composition, and ROI review status. `freeze-data` hashes canonical tables and declares whether the data freeze is ready for baseline or full training. None of these commands trains a model.
