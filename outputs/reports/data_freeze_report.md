# Data Freeze Report

freeze_id: `data_freeze_20260526_v2`
generated_at: `2026-05-26T08:08:36Z`
git_commit: `1ad50e32f3341b0785786457af0b2b580a1904e3`

No DOC model was trained. No DOC prediction or flux product was generated.

## Freeze Readiness
- READY_FOR_BASELINE_TRAINING: `True`
- READY_FOR_FULL_TRAINING: `True`
- frozen_data_training_status: `ready_for_full_training`

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
| hydrobasins                                    | dry_run           |         1 |
| old_arctic_doc_snowmelt_outputs                | downloaded        |         4 |
| old_arctic_doc_snowmelt_untrained_data         | downloaded        |       166 |
| partners_mdpi_eurasian_candidate               | dry_run           |         1 |
| partners_mdpi_eurasian_candidate               | failed            |         2 |
| wqp_usgs_yukon_candidate                       | downloaded        |         6 |
| wqp_usgs_yukon_candidate                       | dry_run           |         1 |
| wqp_usgs_yukon_candidate                       | failed            |         8 |

## Canonical Table Hashes
| table_name                        | local_path                                           |   row_count | sha256                                                           |
|:----------------------------------|:-----------------------------------------------------|------------:|:-----------------------------------------------------------------|
| auxiliary_context_canonical       | data/processed/auxiliary_context_canonical.csv       |       86324 | 83141d2dded2b002f133ed95b65b6b14680e90ae4b6a2fa33dc2c0d821561f7b |
| basin_context_canonical           | data/processed/basin_context_canonical.csv           |           6 | 4116fd1113eaf32ef6d8561831d42c8128524279cfb19e036d0fb85e25b1c6f3 |
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
- basin_context_status: `basin_context_approximate_needs_review`
- basin_context_accepted_for_full_training: `True`
- datastream_final_status_ok: `True`
- mdpi_final_status_ok: `True`
- wqp_final_status_ok: `True`
- gee_regeneration_status: `completed`
- gee_regeneration_accepted_for_full_training: `True`

## Model Readiness Summary
- See `outputs/reports/model_readiness_report.md`.
- model_readiness_exists: `True`

## Test Status
- tests_passed: `True`
- test_summary: `46 passed, 17 warnings in 39.87s`

## Unresolved Blockers
_No critical blockers._

## Explicit Statement
Frozen data are ready for full-training data handoff under the documented v2 rules. No model has been trained by this repository.