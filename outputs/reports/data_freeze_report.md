# Data Freeze Report

freeze_id: `data_freeze_20260526_v3`
generated_at: `2026-05-26T19:23:29Z`
git_commit: `bdee3d26bbeb74fa4a4ae26385ffe0bad02ead1d`

No DOC model was trained. No DOC prediction or flux product was generated.

## Freeze Readiness
- READY_FOR_BASELINE_TRAINING: `True`
- READY_FOR_CORE_FULL_TRAINING: `True`
- READY_FOR_PUBLICATION_GRADE_TRAINING: `True`
- READY_FOR_FULL_TRAINING: `True`
- frozen_data_training_status: `ready_for_publication_grade_training`

## Source Status Summary
| source_id                                      | download_status   |   records |
|:-----------------------------------------------|:------------------|----------:|
| arctic_data_center_tank_2023                   | downloaded        |         1 |
| arcticgro_absorbance_archived                  | manual_required   |         1 |
| arcticgro_absorbance_current                   | downloaded        |         1 |
| arcticgro_data_page                            | downloaded        |         1 |
| arcticgro_discharge_archived                   | manual_required   |         1 |
| arcticgro_discharge_current                    | downloaded        |         7 |
| arcticgro_spatial_data                         | manual_required   |         1 |
| arcticgro_water_quality_archived               | manual_required   |         1 |
| arcticgro_water_quality_current                | downloaded        |         2 |
| arcticgro_water_quality_flags                  | manual_required   |         1 |
| arcticgro_water_quality_metadata               | downloaded        |         1 |
| arcticgro_water_quality_parameter_descriptions | downloaded        |         1 |
| basinatlas_catalog_pdf                         | already_present   |         1 |
| basinatlas_global_gdb                          | already_present   |         1 |
| basinatlas_global_gdb                          | superseded_failed |         1 |
| basinatlas_global_shp_fallback                 | already_present   |         1 |
| datastream_mackenzie_candidate                 | dry_run           |         1 |
| datastream_mackenzie_candidate                 | failed            |         1 |
| gee_era5_land                                  | downloaded        |       156 |
| gee_era5_land                                  | failed            |         1 |
| gee_era5_land                                  | report_only       |         1 |
| gee_hls_s30_l30                                | downloaded        |        60 |
| gee_hls_s30_l30                                | failed            |        60 |
| gee_hls_s30_l30                                | report_only       |         1 |
| gee_landsat_c2_l2                              | downloaded        |       138 |
| gee_landsat_c2_l2                              | report_only       |         1 |
| gee_modis_mod10a1                              | downloaded        |       156 |
| gee_modis_mod10a1                              | failed            |         1 |
| gee_modis_mod10a1                              | report_only       |         1 |
| gee_sentinel2_sr_harmonized                    | downloaded        |        54 |
| gee_sentinel2_sr_harmonized                    | failed            |         1 |
| gee_sentinel2_sr_harmonized                    | report_only       |         1 |
| gee_smap_context_optional                      | failed            |        66 |
| gee_smap_context_optional                      | report_only       |         1 |
| hydroatlas                                     | dry_run           |         1 |
| hydroatlas_technical_documentation             | already_present   |         1 |
| hydrobasins                                    | dry_run           |         1 |
| hydrobasins_custom_lakes_full                  | already_present   |         9 |
| hydrobasins_custom_lakes_full                  | superseded_failed |         9 |
| hydrobasins_pour_points_full                   | already_present   |         1 |
| hydrobasins_pour_points_full                   | superseded_failed |         1 |
| hydrobasins_standard_full                      | already_present   |         9 |
| hydrobasins_standard_full                      | superseded_failed |         9 |
| hydrorivers_global                             | already_present   |        10 |
| hydrorivers_global                             | superseded_failed |        10 |
| hydrorivers_global_fallback_shapefile          | downloaded        |         1 |
| hydrorivers_global_fallback_shapefile          | superseded_failed |         1 |
| lakeatlas_catalog_pdf                          | already_present   |         1 |
| lakeatlas_global_gdb                           | already_present   |         1 |
| lakeatlas_global_gdb                           | superseded_failed |         1 |
| lakeatlas_global_shp_fallback                  | already_present   |         1 |
| old_arctic_doc_snowmelt_outputs                | downloaded        |         4 |
| old_arctic_doc_snowmelt_untrained_data         | downloaded        |       166 |
| partners_mdpi_eurasian_candidate               | dry_run           |         1 |
| partners_mdpi_eurasian_candidate               | failed            |         2 |
| riveratlas_catalog_pdf                         | already_present   |         1 |
| riveratlas_global_gdb                          | already_present   |         1 |
| riveratlas_global_gdb                          | superseded_failed |         1 |
| riveratlas_global_shp_fallback                 | already_present   |         1 |
| wqp_usgs_yukon_candidate                       | downloaded        |        32 |
| wqp_usgs_yukon_candidate                       | dry_run           |         1 |
| wqp_usgs_yukon_candidate                       | failed            |         8 |

## Canonical Table Hashes
| table_name                        | local_path                                           |   row_count | sha256                                                           |
|:----------------------------------|:-----------------------------------------------------|------------:|:-----------------------------------------------------------------|
| auxiliary_context_canonical       | data/processed/auxiliary_context_canonical.csv       |       86324 | 83141d2dded2b002f133ed95b65b6b14680e90ae4b6a2fa33dc2c0d821561f7b |
| basin_context_canonical           | data/processed/basin_context_canonical.csv           |           6 | 9418e0cd2e7ba4aca6024643fe0445439cdf87b6e041fc322c0674a0ea8edcec |
| daily_discharge_canonical         | data/processed/daily_discharge_canonical.csv         |      154370 | 7dfa107c52f636dcb6d28d38d107b5d0b4226d471554103cf5b9e893a2965cdb |
| daily_hydroclimate_canonical      | data/processed/daily_hydroclimate_canonical.csv      |      138432 | e01c47c23dbc9ae600ee441c13294ed702e89a7b263556779e68a33ba597c1a4 |
| doc_labels_canonical              | data/processed/doc_labels_canonical.csv              |         595 | ece38cb8238b21223b72d903da19dc5a01553b32ad50f6ace9a9c56166497657 |
| doc_labels_raw                    | data/processed/doc_labels_raw.csv                    |         595 | 5fd89775032132c8fa10ddebb48b7b0ee0371da81dc9e2ebc7092669c2c93150 |
| lab_optical_proxy_canonical       | data/processed/lab_optical_proxy_canonical.csv       |         882 | e429391241b4261b543e6cebe21c59cfc9e3f53e35c2d5a68d09ce63210adfb4 |
| optical_timeseries_canonical      | data/processed/optical_timeseries_canonical.csv      |      142058 | c7641c4d22122f16c4ad02441ca9b7acacb4d52bc4f2a5a5ae90da4ac4891297 |
| roi_catalog                       | data/processed/roi_catalog.csv                       |          39 | a466966920441f6befbb307bf6d9c746d0d30189a3508a6a72b962a197ade00f |
| training_matrix_daily_predictable | data/processed/training_matrix_daily_predictable.csv |         547 | 9b0adb76091b973b3d732a05dd1faeee7de9e2fabaeb2bee75e00436bcd736d3 |

## Candidate Source Completion
- candidate_label_audit_completed: `True`
- gee_extraction_readiness_completed: `True`
- basin_context_status: `upstream_basin_complete_attributes_partial`
- basin_context_accepted_for_core_full_training: `True`
- basin_context_accepted_for_publication_grade_training: `True`
- datastream_final_status_ok: `True`
- mdpi_final_status_ok: `True`
- wqp_final_status_ok: `True`
- gee_regeneration_status: `completed`
- gee_regeneration_accepted_for_core_full_training: `True`
- gee_regeneration_accepted_for_publication_grade_training: `True`

## GEE Regeneration Final Status
| source_id                   | river     | expected_years   |   successful_chunks |   failed_chunks | remaining_failure_reason_summary   | accepted_for_core_full_training   | accepted_for_publication_grade_training   | notes                                                                         |
|:----------------------------|:----------|:-----------------|--------------------:|----------------:|:-----------------------------------|:----------------------------------|:------------------------------------------|:------------------------------------------------------------------------------|
| gee_hls_s30_l30             | Ob        | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_hls_s30_l30             | Yenisey   | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_hls_s30_l30             | Lena      | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_hls_s30_l30             | Kolyma    | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_hls_s30_l30             | Yukon     | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_hls_s30_l30             | Mackenzie | 2016-2025        |                  10 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Ob        | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Yenisey   | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Lena      | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Kolyma    | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Yukon     | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_sentinel2_sr_harmonized | Mackenzie | 2017-2025        |                   9 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Ob        | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Yenisey   | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Lena      | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Kolyma    | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Yukon     | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_landsat_c2_l2           | Mackenzie | 2003-2025        |                  23 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Ob        | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Yenisey   | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Lena      | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Kolyma    | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Yukon     | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_era5_land               | Mackenzie | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Ob        | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Yenisey   | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Lena      | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Kolyma    | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Yukon     | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_modis_mod10a1           | Mackenzie | 2000-2025        |                  26 |               0 |                                    | True                              | True                                      | Regenerated rows present and current extraction summary has no failed chunks. |
| gee_smap_context_optional   | Ob        | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |
| gee_smap_context_optional   | Yenisey   | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |
| gee_smap_context_optional   | Lena      | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |
| gee_smap_context_optional   | Kolyma    | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |
| gee_smap_context_optional   | Yukon     | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |
| gee_smap_context_optional   | Mackenzie | 2015-2025        |                   0 |               0 |                                    | True                              | False                                     | SMAP is optional and deferred/failed_optional; not a core blocker.            |

## Model Readiness Summary
- See `outputs/reports/model_readiness_report.md`.
- model_readiness_exists: `True`

## Test Status
- tests_passed: `True`
- test_summary: `70 passed, 19 warnings in 47.07s`

## Unresolved Core Blockers
_No critical core blockers._

## Unresolved Publication-Grade Blockers
_No publication-grade blockers._

## Explicit Statement
Frozen data are ready for publication-grade training data handoff under the documented v3 rules. No model has been trained by this repository.