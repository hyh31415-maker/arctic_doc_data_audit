# Data Freeze Report

freeze_id: `data_freeze_20260526_v1`
generated_at: `2026-05-26T04:27:00Z`
git_commit: `4a63b9a662b8616c7df556692476fdbc8f825db7`

No DOC model was trained. No DOC prediction or flux product was generated.

## Freeze Readiness
- READY_FOR_BASELINE_TRAINING: `True`
- READY_FOR_FULL_TRAINING: `False`
- frozen_data_training_status: `ready_for_baseline_not_full`

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
| gee_era5_land                                  | report_only       |         1 |
| gee_hls_s30_l30                                | report_only       |         1 |
| gee_landsat_c2_l2                              | report_only       |         1 |
| gee_modis_mod10a1                              | report_only       |         1 |
| gee_sentinel2_sr_harmonized                    | report_only       |         1 |
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
| basin_context_canonical           | data/processed/basin_context_canonical.csv           |           6 | 93fa2759b675567737accae46637781a9b5c79729a95d3a9c6ad788d7d70eca0 |
| daily_discharge_canonical         | data/processed/daily_discharge_canonical.csv         |      154370 | 7dfa107c52f636dcb6d28d38d107b5d0b4226d471554103cf5b9e893a2965cdb |
| daily_hydroclimate_canonical      | data/processed/daily_hydroclimate_canonical.csv      |       25200 | 09b33be1c903cc255f82e66c296f0f039a2c3f774213d506625400bade446794 |
| doc_labels_canonical              | data/processed/doc_labels_canonical.csv              |         595 | ece38cb8238b21223b72d903da19dc5a01553b32ad50f6ace9a9c56166497657 |
| doc_labels_raw                    | data/processed/doc_labels_raw.csv                    |         595 | 5fd89775032132c8fa10ddebb48b7b0ee0371da81dc9e2ebc7092669c2c93150 |
| lab_optical_proxy_canonical       | data/processed/lab_optical_proxy_canonical.csv       |         882 | e429391241b4261b543e6cebe21c59cfc9e3f53e35c2d5a68d09ce63210adfb4 |
| optical_timeseries_canonical      | data/processed/optical_timeseries_canonical.csv      |       49362 | b87175bafa4aed3564575925db665674ad7cefbe159b24de6b741c8182a6b8b3 |
| roi_catalog                       | data/processed/roi_catalog.csv                       |          39 | a466966920441f6befbb307bf6d9c746d0d30189a3508a6a72b962a197ade00f |
| training_matrix_daily_predictable | data/processed/training_matrix_daily_predictable.csv |         547 | f7928fa392d0bd39037f8b50447ea9def8df1417f21dab129447db9e2464de61 |

## Candidate Source Completion
- candidate_label_audit_completed: `True`
- gee_extraction_readiness_completed: `True`
- basin_context_status: `placeholder_only`

## Model Readiness Summary
- See `outputs/reports/model_readiness_report.md`.
- model_readiness_exists: `True`

## Test Status
- tests_passed: `True`
- test_summary: `35 passed in 19.54s`

## Unresolved Blockers
- Basin context status is placeholder_only.

## Explicit Statement
Frozen data are ready for baseline training only if the readiness flag above is true. Full training must wait until all candidate sources and basin/GEE regeneration blockers are resolved.
