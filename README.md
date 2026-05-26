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
python -m arctic_doc_data_audit.cli gee-auth-check
python -m arctic_doc_data_audit.cli run-gee-extraction --all
python -m arctic_doc_data_audit.cli complete-basin-context
python -m arctic_doc_data_audit.cli finalize-candidate-sources --defer-datastream
python -m arctic_doc_data_audit.cli qa-data
python -m arctic_doc_data_audit.cli fix-gee-failures --all
python -m arctic_doc_data_audit.cli discover-wqp-characteristics
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
make final-data-clean
make build-gold-tables
make build-model-input-matrices
make freeze-gold-data
make gee-auth-check
make run-gee-extraction
make complete-basin-context
make finalize-candidate-sources
make qa-data
make fix-gee-failures
make discover-wqp-characteristics
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

## Full Data Completion v2

When Earth Engine credentials are available locally, run the v2 completion flow:

```powershell
python -m arctic_doc_data_audit.cli gee-auth-check
python -m arctic_doc_data_audit.cli run-gee-extraction --all
python -m arctic_doc_data_audit.cli complete-basin-context
python -m arctic_doc_data_audit.cli finalize-candidate-sources --defer-datastream
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_YYYYMMDD_v2
```

Regenerated GEE rows use non-legacy source ids (`gee_hls_s30_l30`, `gee_sentinel2_sr_harmonized`, `gee_landsat_c2_l2`, `gee_era5_land`, `gee_modis_mod10a1`). Legacy snapshot rows remain auditable reference rows, while the training matrix prefers regenerated hydroclimate when both are present. DataStream can be explicitly deferred with `--defer-datastream`; MDPI supplements remain optional/manual mechanism context after HTTP 403. The freeze report still states that no model, DOC prediction, or flux product was generated.

## Data QA & Freeze v3

Before any training handoff, run the v3 QA flow:

```powershell
python -m arctic_doc_data_audit.cli qa-data
python -m arctic_doc_data_audit.cli fix-gee-failures --all
python -m arctic_doc_data_audit.cli discover-wqp-characteristics
python -m arctic_doc_data_audit.cli finalize-candidate-sources --defer-datastream
python -m arctic_doc_data_audit.cli rebuild-training-matrix-v3
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_YYYYMMDD_v3
```

v3 uses three readiness flags: baseline, core full, and publication grade. Approximate ROI-derived basin context can support core full training when basin-level attributes are not model inputs, but it does not satisfy publication-grade readiness. Publication-grade training requires real HydroBASINS/HydroATLAS upstream basin context and documented resolution of GEE/ROI issues.

## Full HydroSHEDS / HydroATLAS Completion

For publication-grade basin context, run the full HydroSHEDS/HydroATLAS workflow. Raw zip, geodatabase, shapefile, and unpacked files are written under `data/raw_external/hydrosheds_full/`, remain gitignored, and are represented only by manifest, index, and report rows.

```powershell
python -m arctic_doc_data_audit.cli download-hydrosheds-full --all
python -m arctic_doc_data_audit.cli index-hydrosheds-full
python -m arctic_doc_data_audit.cli match-stations-to-hydrorivers
python -m arctic_doc_data_audit.cli match-stations-to-hydrobasins
python -m arctic_doc_data_audit.cli build-upstream-basin-context
python -m arctic_doc_data_audit.cli extract-hydroatlas-attributes
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_YYYYMMDD_v3
```

The workflow parses official HydroSHEDS product pages first and uses `configs/hydrosheds_full.yaml` manual URLs only as a fallback. HydroATLAS package downloads use stable `https://ndownloader.figshare.com/files/<file_id>` links to avoid the `figshare.com/ndownloader` WAF challenge; documentation and catalogs use `data.hydrosheds.org` PDF links. Station snapping uses HydroRIVERS; station basin matching uses HydroBASINS levels 6-9; upstream membership is built from `NEXT_DOWN` topology and never from ROI area. Publication-grade readiness is true only when all six rivers have upstream HydroBASINS context plus HydroATLAS attributes marked as complete or partial.

The full HydroATLAS list is `BasinATLAS_Data_v10.gdb.zip`, `BasinATLAS_Data_v10_shp.zip`, `RiverATLAS_Data_v10.gdb.zip`, `RiverATLAS_Data_v10_shp.zip`, `LakeATLAS_Data_v10.gdb.zip`, `LakeATLAS_Data_v10_shp.zip`, `HydroATLAS_TechDoc_v10_1.pdf`, `BasinATLAS_Catalog_v10.pdf`, `RiverATLAS_Catalog_v10.pdf`, and `LakeATLAS_Catalog_v10.pdf`. GDB packages are unpacked because attribute extraction needs readable layers; SHP fallback packages and PDFs are downloaded and hash-checked but not unpacked by default.

## Gold Data Freeze

After publication-grade acquisition is complete, lock the modeling handoff with the gold freeze workflow:

```powershell
python -m arctic_doc_data_audit.cli final-data-clean
python -m arctic_doc_data_audit.cli build-gold-tables
python -m arctic_doc_data_audit.cli build-model-input-matrices
python -m arctic_doc_data_audit.cli model-readiness
python -m arctic_doc_data_audit.cli freeze-gold-data --freeze-id data_freeze_gold_YYYYMMDD_v1
```

Gold commands read only the existing canonical/audit/manifest layer and write fixed outputs under `data/processed/gold/` plus audit artifacts under `outputs/reports/gold/` and `outputs/tables/gold/`. They do not query new sources, train DOC models, generate DOC predictions, or generate flux.

After gold freeze, modeling projects should read only:

- `data/processed/gold/training_matrix_hydrocore.csv`
- `data/processed/gold/training_matrix_basin_context.csv`
- `data/processed/gold/training_matrix_optical_matched_*.csv`
- `data/processed/gold/prediction_grid_daily_hydrocore.csv`

The gold production matrices exclude lab absorbance/CDOM (`A254`, `A375`, `A440`, `SUVA254`, spectral slopes). Optical reflectance stays an optical sensitivity predictor, not a DOC observation. HydroATLAS identifiers and topology fields remain metadata and are not model predictors. If processed gold CSVs are not committed, the freeze report, table hashes, data dictionary, QA tables, and reproduction commands define the fixed handoff.
