# Gold Data Freeze Report

freeze_id: `data_freeze_gold_20260526_v1`
generated_at_utc: `2026-05-26T20:27:51Z`
git_commit_at_generation: `22ddcb00630d4713a195c6d2a2517877979eabcc`
input_freeze_id: `data_freeze_20260526_v3`

No DOC model was trained. No DOC prediction was generated. No flux was generated.

Future modeling should read only `data/processed/gold/*`.

## Readiness Flags
- GOLD_FREEZE_READY: `True`
- QA_CRITICAL_ISSUES: `0`
- QA_HIGH_BLOCKING_ISSUES: `0`
- TESTS_PASSED: `True`

## Gold Table Hashes
| table_name                                       | local_path                                                           |   row_count | sha256                                                           | exists   |
|:-------------------------------------------------|:---------------------------------------------------------------------|------------:|:-----------------------------------------------------------------|:---------|
| basin_attributes_curated.csv                     | data/processed/gold/basin_attributes_curated.csv                     |         240 | 6e4d18f8acd58f90a1563b89692e7030fa0464ce7ebdd6a38a4691538a27b171 | True     |
| basin_attributes_curated_wide.csv                | data/processed/gold/basin_attributes_curated_wide.csv                |           6 | 17d4197092bb423ba23a4451521ead9b8416212d4daadc173dd871548b0d9d77 | True     |
| basin_context_gold.csv                           | data/processed/gold/basin_context_gold.csv                           |           6 | 9910dd6e37df1034e572ae11f468727e1024f7cd398b38ee0e8b6521a5a6e96d | True     |
| daily_discharge_gold.csv                         | data/processed/gold/daily_discharge_gold.csv                         |      154370 | a351eb43849fda32881890beb77ba84ed74e8b99f382e9cfe38b527b74ac4908 | True     |
| daily_hydroclimate_gold.csv                      | data/processed/gold/daily_hydroclimate_gold.csv                      |       52726 | 26722d1cfef703b353a13ffd2ff5209c5e5a073290ff1a09223beb09af7b55fe | True     |
| doc_labels_gold.csv                              | data/processed/gold/doc_labels_gold.csv                              |         547 | ac0935691515952075b455061cff9ef8a04f5b58ccdd127e9e5ca6e06c8f6b71 | True     |
| lab_optical_proxy_gold.csv                       | data/processed/gold/lab_optical_proxy_gold.csv                       |         882 | 4db6f16f4ee980fe7e7292f73bae780932a0d0c14ba20dee5fd1b69bea986139 | True     |
| optical_match_candidates_0d.csv                  | data/processed/gold/optical_match_candidates_0d.csv                  |        1307 | a33816123ffb3b1d8cc63e1ba326f8ad29eb84b2f17de882097f63ee901d6758 | True     |
| optical_match_candidates_1d.csv                  | data/processed/gold/optical_match_candidates_1d.csv                  |        4085 | e7c458a67b95a218b56616e10189c905755318ad4fc32228ed3676f916e71491 | True     |
| optical_match_candidates_3d.csv                  | data/processed/gold/optical_match_candidates_3d.csv                  |        9611 | 6a639d1fdb52319e8e373df4ce8e79b82b9c6b1837764cb921e8a1647c67e426 | True     |
| optical_match_candidates_7d.csv                  | data/processed/gold/optical_match_candidates_7d.csv                  |       21109 | 7008735b5df087c6edb1913547ffac7f0923380e08855b73779ed3f2e808dd38 | True     |
| optical_timeseries_gold.csv                      | data/processed/gold/optical_timeseries_gold.csv                      |      142058 | 93e647e53c4fe6668d3a8b7f7477138b2ed3d809bb7f8b9eedb3173e51e07e62 | True     |
| prediction_grid_daily_hydrocore.csv              | data/processed/gold/prediction_grid_daily_hydrocore.csv              |       52594 | 3ba36c79ad53b14e6b9d08e699bb995a9f694d4ffe75d4565126fb84cec4767b | True     |
| prediction_grid_daily_with_basin_context.csv     | data/processed/gold/prediction_grid_daily_with_basin_context.csv     |       52594 | 7e6d0800f6c99ba0a486cf1d8ef2d0bb705e3973121b0466b152976802211bc4 | True     |
| roi_catalog_gold.csv                             | data/processed/gold/roi_catalog_gold.csv                             |          39 | a466966920441f6befbb307bf6d9c746d0d30189a3508a6a72b962a197ade00f | True     |
| training_matrix_basin_context.csv                | data/processed/gold/training_matrix_basin_context.csv                |         547 | 2dbcd48e094cade5ef0053f9400f8cc1615e64cd9a9a6c96c165782f92f10522 | True     |
| training_matrix_hydrocore.csv                    | data/processed/gold/training_matrix_hydrocore.csv                    |         547 | 0b4eaf0ebf716e23379f15d56cbff82c105251497346b29aa82c8adba95db8e1 | True     |
| training_matrix_optical_matched_0d.csv           | data/processed/gold/training_matrix_optical_matched_0d.csv           |         188 | 630c57dddd749c9034db2bdfa40137a512392db926112111fd512803aac2a682 | True     |
| training_matrix_optical_matched_1d.csv           | data/processed/gold/training_matrix_optical_matched_1d.csv           |         297 | 0ee52cd1851e69a537eb6afe2962260a46cd3ac9dbc2e301950f3ce18fa4518b | True     |
| training_matrix_optical_matched_3d.csv           | data/processed/gold/training_matrix_optical_matched_3d.csv           |         374 | b5413d3da3470e20255ff1dc851beeeb062b0c2a16acbc1d747a497f100e3fcc | True     |
| training_matrix_optical_matched_3d_hls.csv       | data/processed/gold/training_matrix_optical_matched_3d_hls.csv       |         144 | 2f00be03cef96c468d934781d4404cd83c9022d2b4a3dd0eafa20cec831eb471 | True     |
| training_matrix_optical_matched_3d_landsat.csv   | data/processed/gold/training_matrix_optical_matched_3d_landsat.csv   |         184 | f5a7a3b0e9d3e0829730788c893a1be85d291c6a18cdb7e3d4dc3caff8fb9635 | True     |
| training_matrix_optical_matched_3d_sentinel2.csv | data/processed/gold/training_matrix_optical_matched_3d_sentinel2.csv |          46 | 0d2fa15318d8eec6af2a96d5aa2ac7a01f47dcc89689356926b8ebf4a496bd12 | True     |
| training_matrix_optical_matched_7d.csv           | data/processed/gold/training_matrix_optical_matched_7d.csv           |         420 | 6110815762d71a0eb251413ed6625068c533776f82c058c366d9f6cf8b66d413 | True     |

## Model Input Matrix Hashes
| table_name                                       | local_path                                                           |   row_count | sha256                                                           | exists   |
|:-------------------------------------------------|:---------------------------------------------------------------------|------------:|:-----------------------------------------------------------------|:---------|
| prediction_grid_daily_hydrocore.csv              | data/processed/gold/prediction_grid_daily_hydrocore.csv              |       52594 | 3ba36c79ad53b14e6b9d08e699bb995a9f694d4ffe75d4565126fb84cec4767b | True     |
| prediction_grid_daily_with_basin_context.csv     | data/processed/gold/prediction_grid_daily_with_basin_context.csv     |       52594 | 7e6d0800f6c99ba0a486cf1d8ef2d0bb705e3973121b0466b152976802211bc4 | True     |
| training_matrix_basin_context.csv                | data/processed/gold/training_matrix_basin_context.csv                |         547 | 2dbcd48e094cade5ef0053f9400f8cc1615e64cd9a9a6c96c165782f92f10522 | True     |
| training_matrix_hydrocore.csv                    | data/processed/gold/training_matrix_hydrocore.csv                    |         547 | 0b4eaf0ebf716e23379f15d56cbff82c105251497346b29aa82c8adba95db8e1 | True     |
| training_matrix_optical_matched_0d.csv           | data/processed/gold/training_matrix_optical_matched_0d.csv           |         188 | 630c57dddd749c9034db2bdfa40137a512392db926112111fd512803aac2a682 | True     |
| training_matrix_optical_matched_1d.csv           | data/processed/gold/training_matrix_optical_matched_1d.csv           |         297 | 0ee52cd1851e69a537eb6afe2962260a46cd3ac9dbc2e301950f3ce18fa4518b | True     |
| training_matrix_optical_matched_3d.csv           | data/processed/gold/training_matrix_optical_matched_3d.csv           |         374 | b5413d3da3470e20255ff1dc851beeeb062b0c2a16acbc1d747a497f100e3fcc | True     |
| training_matrix_optical_matched_3d_hls.csv       | data/processed/gold/training_matrix_optical_matched_3d_hls.csv       |         144 | 2f00be03cef96c468d934781d4404cd83c9022d2b4a3dd0eafa20cec831eb471 | True     |
| training_matrix_optical_matched_3d_landsat.csv   | data/processed/gold/training_matrix_optical_matched_3d_landsat.csv   |         184 | f5a7a3b0e9d3e0829730788c893a1be85d291c6a18cdb7e3d4dc3caff8fb9635 | True     |
| training_matrix_optical_matched_3d_sentinel2.csv | data/processed/gold/training_matrix_optical_matched_3d_sentinel2.csv |          46 | 0d2fa15318d8eec6af2a96d5aa2ac7a01f47dcc89689356926b8ebf4a496bd12 | True     |
| training_matrix_optical_matched_7d.csv           | data/processed/gold/training_matrix_optical_matched_7d.csv           |         420 | 6110815762d71a0eb251413ed6625068c533776f82c058c366d9f6cf8b66d413 | True     |

## Source Composition
| table_name                                       | source_column          | source_id                                                             |   rows |
|:-------------------------------------------------|:-----------------------|:----------------------------------------------------------------------|-------:|
| basin_attributes_curated.csv                     | source_id              | hydrobasins_standard_full;basinatlas_global_gdb;riveratlas_global_gdb |    240 |
| basin_attributes_curated_wide.csv                |                        | no_source_column                                                      |      6 |
| basin_context_gold.csv                           | source_id              | hydrobasins_standard_full;basinatlas_global_gdb;riveratlas_global_gdb |      6 |
| daily_discharge_gold.csv                         | source_id              | arcticgro_discharge_current                                           | 154370 |
| daily_hydroclimate_gold.csv                      | source_id_temperature  |                                                                       |   1041 |
| daily_hydroclimate_gold.csv                      | source_id_temperature  | gee_era5_land                                                         |  47485 |
| daily_hydroclimate_gold.csv                      | source_id_temperature  | old_arctic_doc_snowmelt_untrained_data                                |   4200 |
| daily_hydroclimate_gold.csv                      | source_id_snow         |                                                                       |  19049 |
| daily_hydroclimate_gold.csv                      | source_id_snow         | gee_modis_mod10a1                                                     |  17363 |
| daily_hydroclimate_gold.csv                      | source_id_snow         | old_arctic_doc_snowmelt_untrained_data                                |  16314 |
| daily_hydroclimate_gold.csv                      | source_id_runoff       |                                                                       |   1041 |
| daily_hydroclimate_gold.csv                      | source_id_runoff       | gee_era5_land                                                         |  47485 |
| daily_hydroclimate_gold.csv                      | source_id_runoff       | old_arctic_doc_snowmelt_untrained_data                                |   4200 |
| doc_labels_gold.csv                              | source_id              | arcticgro_water_quality_current                                       |    547 |
| lab_optical_proxy_gold.csv                       | source_id              | arcticgro_absorbance_current                                          |    442 |
| lab_optical_proxy_gold.csv                       | source_id              | arcticgro_water_quality_current                                       |    440 |
| optical_match_candidates_0d.csv                  | source_id              | gee_hls_s30_l30                                                       |    652 |
| optical_match_candidates_0d.csv                  | source_id              | gee_landsat_c2_l2                                                     |    107 |
| optical_match_candidates_0d.csv                  | source_id              | gee_sentinel2_sr_harmonized                                           |     99 |
| optical_match_candidates_0d.csv                  | source_id              | old_arctic_doc_snowmelt_untrained_data                                |    449 |
| optical_match_candidates_1d.csv                  | source_id              | gee_hls_s30_l30                                                       |   2050 |
| optical_match_candidates_1d.csv                  | source_id              | gee_landsat_c2_l2                                                     |    319 |
| optical_match_candidates_1d.csv                  | source_id              | gee_sentinel2_sr_harmonized                                           |    286 |
| optical_match_candidates_1d.csv                  | source_id              | old_arctic_doc_snowmelt_untrained_data                                |   1430 |
| optical_match_candidates_3d.csv                  | source_id              | gee_hls_s30_l30                                                       |   4858 |
| optical_match_candidates_3d.csv                  | source_id              | gee_landsat_c2_l2                                                     |    678 |
| optical_match_candidates_3d.csv                  | source_id              | gee_sentinel2_sr_harmonized                                           |    670 |
| optical_match_candidates_3d.csv                  | source_id              | old_arctic_doc_snowmelt_untrained_data                                |   3405 |
| optical_match_candidates_7d.csv                  | source_id              | gee_hls_s30_l30                                                       |  10758 |
| optical_match_candidates_7d.csv                  | source_id              | gee_landsat_c2_l2                                                     |   1402 |
| optical_match_candidates_7d.csv                  | source_id              | gee_sentinel2_sr_harmonized                                           |   1422 |
| optical_match_candidates_7d.csv                  | source_id              | old_arctic_doc_snowmelt_untrained_data                                |   7527 |
| optical_timeseries_gold.csv                      | source_id              | gee_hls_s30_l30                                                       |  74347 |
| optical_timeseries_gold.csv                      | source_id              | gee_landsat_c2_l2                                                     |   6936 |
| optical_timeseries_gold.csv                      | source_id              | gee_sentinel2_sr_harmonized                                           |  11413 |
| optical_timeseries_gold.csv                      | source_id              | old_arctic_doc_snowmelt_untrained_data                                |  49362 |
| prediction_grid_daily_hydrocore.csv              | source_id_discharge    | arcticgro_discharge_current                                           |  52594 |
| prediction_grid_daily_hydrocore.csv              | source_id_hydroclimate |                                                                       |   1041 |
| prediction_grid_daily_hydrocore.csv              | source_id_hydroclimate | gee_era5_land                                                         |  47353 |
| prediction_grid_daily_hydrocore.csv              | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |   4200 |
| prediction_grid_daily_with_basin_context.csv     | source_id_discharge    | arcticgro_discharge_current                                           |  52594 |
| prediction_grid_daily_with_basin_context.csv     | source_id_hydroclimate |                                                                       |   1041 |
| prediction_grid_daily_with_basin_context.csv     | source_id_hydroclimate | gee_era5_land                                                         |  47353 |
| prediction_grid_daily_with_basin_context.csv     | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |   4200 |
| roi_catalog_gold.csv                             | source_id              | old_arctic_doc_snowmelt_untrained_data                                |     39 |
| training_matrix_basin_context.csv                | source_id_label        | arcticgro_water_quality_current                                       |    547 |
| training_matrix_basin_context.csv                | source_id_discharge    | arcticgro_discharge_current                                           |    547 |
| training_matrix_basin_context.csv                | source_id_hydroclimate |                                                                       |     34 |
| training_matrix_basin_context.csv                | source_id_hydroclimate | gee_era5_land                                                         |    460 |
| training_matrix_basin_context.csv                | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     53 |
| training_matrix_hydrocore.csv                    | source_id_label        | arcticgro_water_quality_current                                       |    547 |
| training_matrix_hydrocore.csv                    | source_id_discharge    | arcticgro_discharge_current                                           |    547 |
| training_matrix_hydrocore.csv                    | source_id_hydroclimate |                                                                       |     34 |
| training_matrix_hydrocore.csv                    | source_id_hydroclimate | gee_era5_land                                                         |    460 |
| training_matrix_hydrocore.csv                    | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     53 |
| training_matrix_optical_matched_0d.csv           | source_id_optical      | gee_hls_s30_l30                                                       |     98 |
| training_matrix_optical_matched_0d.csv           | source_id_optical      | gee_landsat_c2_l2                                                     |     54 |
| training_matrix_optical_matched_0d.csv           | source_id_optical      | gee_sentinel2_sr_harmonized                                           |     36 |
| training_matrix_optical_matched_0d.csv           | source_id_hydroclimate |                                                                       |      9 |
| training_matrix_optical_matched_0d.csv           | source_id_hydroclimate | gee_era5_land                                                         |    159 |
| training_matrix_optical_matched_0d.csv           | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     20 |
| training_matrix_optical_matched_1d.csv           | source_id_optical      | gee_hls_s30_l30                                                       |    137 |
| training_matrix_optical_matched_1d.csv           | source_id_optical      | gee_landsat_c2_l2                                                     |    115 |
| training_matrix_optical_matched_1d.csv           | source_id_optical      | gee_sentinel2_sr_harmonized                                           |     45 |
| training_matrix_optical_matched_1d.csv           | source_id_hydroclimate |                                                                       |     10 |
| training_matrix_optical_matched_1d.csv           | source_id_hydroclimate | gee_era5_land                                                         |    252 |
| training_matrix_optical_matched_1d.csv           | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     35 |
| training_matrix_optical_matched_3d.csv           | source_id_optical      | gee_hls_s30_l30                                                       |    144 |
| training_matrix_optical_matched_3d.csv           | source_id_optical      | gee_landsat_c2_l2                                                     |    184 |
| training_matrix_optical_matched_3d.csv           | source_id_optical      | gee_sentinel2_sr_harmonized                                           |     46 |
| training_matrix_optical_matched_3d.csv           | source_id_hydroclimate |                                                                       |     13 |
| training_matrix_optical_matched_3d.csv           | source_id_hydroclimate | gee_era5_land                                                         |    320 |
| training_matrix_optical_matched_3d.csv           | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     41 |
| training_matrix_optical_matched_3d_hls.csv       | source_id_optical      | gee_hls_s30_l30                                                       |    144 |
| training_matrix_optical_matched_3d_hls.csv       | source_id_hydroclimate |                                                                       |     12 |
| training_matrix_optical_matched_3d_hls.csv       | source_id_hydroclimate | gee_era5_land                                                         |    120 |
| training_matrix_optical_matched_3d_hls.csv       | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     12 |
| training_matrix_optical_matched_3d_landsat.csv   | source_id_optical      | gee_landsat_c2_l2                                                     |    184 |
| training_matrix_optical_matched_3d_landsat.csv   | source_id_hydroclimate |                                                                       |      1 |
| training_matrix_optical_matched_3d_landsat.csv   | source_id_hydroclimate | gee_era5_land                                                         |    157 |
| training_matrix_optical_matched_3d_landsat.csv   | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     26 |
| training_matrix_optical_matched_3d_sentinel2.csv | source_id_optical      | gee_sentinel2_sr_harmonized                                           |     46 |
| training_matrix_optical_matched_3d_sentinel2.csv | source_id_hydroclimate | gee_era5_land                                                         |     43 |
| training_matrix_optical_matched_3d_sentinel2.csv | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |      3 |
| training_matrix_optical_matched_7d.csv           | source_id_optical      | gee_hls_s30_l30                                                       |    147 |
| training_matrix_optical_matched_7d.csv           | source_id_optical      | gee_landsat_c2_l2                                                     |    226 |
| training_matrix_optical_matched_7d.csv           | source_id_optical      | gee_sentinel2_sr_harmonized                                           |     47 |
| training_matrix_optical_matched_7d.csv           | source_id_hydroclimate |                                                                       |     15 |
| training_matrix_optical_matched_7d.csv           | source_id_hydroclimate | gee_era5_land                                                         |    355 |
| training_matrix_optical_matched_7d.csv           | source_id_hydroclimate | old_arctic_doc_snowmelt_untrained_data                                |     50 |

## QA Summary
| issue_id     | severity   | table_name                  | column_name      | river   | date   | issue_type       | description                                          | blocking_for_gold_freeze   | blocking_for_modeling   | recommended_action                              | resolution_status     | notes                                                                               |
|:-------------|:-----------|:----------------------------|:-----------------|:--------|:-------|:-----------------|:-----------------------------------------------------|:---------------------------|:------------------------|:------------------------------------------------|:----------------------|:------------------------------------------------------------------------------------|
| GOLD-QA-0001 | low        | daily_hydroclimate_gold.csv | snowmelt_m       |         |        | range_check_flag | 137 rows are outside the configured screening range. | False                      | False                   | Track as non-fatal QA note or sensitivity item. | accepted_non_blocking | Flagged for review; not a gold freeze blocker unless confirmed as a fatal data bug. |
| GOLD-QA-0002 | low        | daily_hydroclimate_gold.csv | surface_runoff_m |         |        | range_check_flag | 71 rows are outside the configured screening range.  | False                      | False                   | Track as non-fatal QA note or sensitivity item. | accepted_non_blocking | Flagged for review; not a gold freeze blocker unless confirmed as a fatal data bug. |

## Data Dictionary
- rows: `652`
- report: `outputs/reports/gold/data_dictionary_gold.md`

## Fatal Data Bug Policy Summary
Open a new freeze version only for fatal data bugs such as DOC/TOC confusion, unit conversion errors, duplicate/preferred label errors, GEE band mapping errors, basin aggregation errors, lab optical leakage, corrupt raw files, or hash mismatches.