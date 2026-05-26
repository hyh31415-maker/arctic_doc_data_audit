# Data Availability Report

This report audits data acquisition and preprocessing readiness only. No DOC model was trained.

## 1. Download Status Summary
| source_id                                      | download_status   | failure_reason                                                                                                     |   file_count |
|:-----------------------------------------------|:------------------|:-------------------------------------------------------------------------------------------------------------------|-------------:|
| arctic_data_center_tank_2023                   | dry_run           | Dry-run only. Resolve DOI and review package members before bulk download.                                         |            1 |
| arcticgro_absorbance_archived                  | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_absorbance_current                   | downloaded        |                                                                                                                    |            1 |
| arcticgro_data_page                            | downloaded        |                                                                                                                    |            1 |
| arcticgro_discharge_archived                   | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_discharge_current                    | downloaded        |                                                                                                                    |            7 |
| arcticgro_spatial_data                         | manual_required   | Spatial folder may contain multiple files; manual review required before download.                                 |            1 |
| arcticgro_water_quality_archived               | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_water_quality_current                | downloaded        |                                                                                                                    |            2 |
| arcticgro_water_quality_flags                  | manual_required   | Flag codes are extracted during preprocessing from the Water Quality workbook.                                     |            1 |
| arcticgro_water_quality_metadata               | downloaded        |                                                                                                                    |            1 |
| arcticgro_water_quality_parameter_descriptions | downloaded        |                                                                                                                    |            1 |
| datastream_mackenzie_candidate                 | dry_run           | Use DataStream API/hub search for Mackenzie DOC/TOC/CDOM/UV/turbidity candidates; keep candidate-only QC.          |            1 |
| gee_era5_land                                  | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| gee_hls_s30_l30                                | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_landsat_c2_l2                              | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_modis_mod10a1                              | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| gee_sentinel2_sr_harmonized                    | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_smap_context_optional                      | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| hydroatlas                                     | dry_run           | Large HydroSHEDS products require size/license review; provide local files via configs/local_paths.yaml.           |            1 |
| hydrobasins                                    | dry_run           | Large HydroSHEDS products require size/license review; provide local files via configs/local_paths.yaml.           |            1 |
| old_arctic_doc_snowmelt_outputs                | downloaded        |                                                                                                                    |            4 |
| old_arctic_doc_snowmelt_untrained_data         | downloaded        |                                                                                                                    |          166 |
| partners_mdpi_eurasian_candidate               | dry_run           | Search/download supplementary tables conservatively and preserve article/source citation before parsing.           |            1 |
| wqp_usgs_yukon_candidate                       | dry_run           | Candidate query only; results need label QC before use.                                                            |            1 |

## 2. Source-Level Files, Status, and Failures
| source_id                                      | download_status   | failure_reason                                                                                                     |   file_count |
|:-----------------------------------------------|:------------------|:-------------------------------------------------------------------------------------------------------------------|-------------:|
| arctic_data_center_tank_2023                   | dry_run           | Dry-run only. Resolve DOI and review package members before bulk download.                                         |            1 |
| arcticgro_absorbance_archived                  | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_absorbance_current                   | downloaded        |                                                                                                                    |            1 |
| arcticgro_data_page                            | downloaded        |                                                                                                                    |            1 |
| arcticgro_discharge_archived                   | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_discharge_current                    | downloaded        |                                                                                                                    |            7 |
| arcticgro_spatial_data                         | manual_required   | Spatial folder may contain multiple files; manual review required before download.                                 |            1 |
| arcticgro_water_quality_archived               | manual_required   | Google Drive archive folder is not bulk-downloaded automatically.                                                  |            1 |
| arcticgro_water_quality_current                | downloaded        |                                                                                                                    |            2 |
| arcticgro_water_quality_flags                  | manual_required   | Flag codes are extracted during preprocessing from the Water Quality workbook.                                     |            1 |
| arcticgro_water_quality_metadata               | downloaded        |                                                                                                                    |            1 |
| arcticgro_water_quality_parameter_descriptions | downloaded        |                                                                                                                    |            1 |
| datastream_mackenzie_candidate                 | dry_run           | Use DataStream API/hub search for Mackenzie DOC/TOC/CDOM/UV/turbidity candidates; keep candidate-only QC.          |            1 |
| gee_era5_land                                  | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| gee_hls_s30_l30                                | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_landsat_c2_l2                              | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_modis_mod10a1                              | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| gee_sentinel2_sr_harmonized                    | report_only       | Earth Engine extraction not executed. rivers=all; years=2017-2025; roi_set=default. Authenticate EE before export. |            1 |
| gee_smap_context_optional                      | report_only       | Earth Engine hydroclimate extraction not executed. rivers=all; years=2000-2025; roi_set=basin.                     |            1 |
| hydroatlas                                     | dry_run           | Large HydroSHEDS products require size/license review; provide local files via configs/local_paths.yaml.           |            1 |
| hydrobasins                                    | dry_run           | Large HydroSHEDS products require size/license review; provide local files via configs/local_paths.yaml.           |            1 |
| old_arctic_doc_snowmelt_outputs                | downloaded        |                                                                                                                    |            4 |
| old_arctic_doc_snowmelt_untrained_data         | downloaded        |                                                                                                                    |          166 |
| partners_mdpi_eurasian_candidate               | dry_run           | Search/download supplementary tables conservatively and preserve article/source citation before parsing.           |            1 |
| wqp_usgs_yukon_candidate                       | dry_run           | Candidate query only; results need label QC before use.                                                            |            1 |

## 3. DOC Label Counts by River
| river     |   raw_count |   canonical_count |   Tier_A |   Tier_B |   Tier_C |   Tier_D |   can_train_doc_model |   can_train_daily_flux_model |
|:----------|------------:|------------------:|---------:|---------:|---------:|---------:|----------------------:|-----------------------------:|
| Ob        |          99 |                99 |       75 |       12 |        0 |       12 |                    87 |                           87 |
| Yenisey   |          98 |                98 |       75 |       12 |        0 |       11 |                    87 |                           87 |
| Lena      |          98 |                98 |       75 |       12 |        0 |       11 |                    87 |                           87 |
| Kolyma    |          98 |                98 |       75 |       12 |        0 |       11 |                    87 |                           87 |
| Yukon     |          99 |                99 |       75 |       21 |        0 |        3 |                    96 |                           96 |
| Mackenzie |         103 |               103 |       76 |       27 |        0 |        0 |                   103 |                          103 |

## 4. DOC Label Counts by River and Year
| river     |   year |   doc_label_count |
|:----------|-------:|------------------:|
| Kolyma    |   2003 |                 1 |
| Kolyma    |   2004 |                 7 |
| Kolyma    |   2005 |                 7 |
| Kolyma    |   2006 |                 2 |
| Kolyma    |   2009 |                 5 |
| Kolyma    |   2010 |                 5 |
| Kolyma    |   2011 |                 5 |
| Kolyma    |   2012 |                 4 |
| Kolyma    |   2013 |                 5 |
| Kolyma    |   2014 |                 6 |
| Kolyma    |   2015 |                 6 |
| Kolyma    |   2016 |                 6 |
| Kolyma    |   2017 |                 6 |
| Kolyma    |   2018 |                 6 |
| Kolyma    |   2019 |                 4 |
| Kolyma    |   2020 |                 6 |
| Kolyma    |   2021 |                 6 |
| Kolyma    |   2022 |                 6 |
| Kolyma    |   2023 |                 5 |
| Lena      |   2003 |                 1 |
| Lena      |   2004 |                 7 |
| Lena      |   2005 |                 7 |
| Lena      |   2006 |                 2 |
| Lena      |   2009 |                 5 |
| Lena      |   2010 |                 5 |
| Lena      |   2011 |                 5 |
| Lena      |   2012 |                 4 |
| Lena      |   2013 |                 6 |
| Lena      |   2014 |                 6 |
| Lena      |   2015 |                 6 |
| Lena      |   2016 |                 6 |
| Lena      |   2017 |                 6 |
| Lena      |   2018 |                 6 |
| Lena      |   2019 |                 4 |
| Lena      |   2020 |                 6 |
| Lena      |   2021 |                 6 |
| Lena      |   2022 |                 6 |
| Lena      |   2023 |                 4 |
| Mackenzie |   2003 |                 1 |
| Mackenzie |   2004 |                 7 |
| Mackenzie |   2005 |                 7 |
| Mackenzie |   2006 |                 1 |
| Mackenzie |   2007 |                 1 |
| Mackenzie |   2009 |                 4 |
| Mackenzie |   2010 |                 5 |
| Mackenzie |   2011 |                 5 |
| Mackenzie |   2012 |                 5 |
| Mackenzie |   2013 |                 6 |
| Mackenzie |   2014 |                 6 |
| Mackenzie |   2015 |                 6 |
| Mackenzie |   2016 |                 6 |
| Mackenzie |   2017 |                 6 |
| Mackenzie |   2018 |                 6 |
| Mackenzie |   2019 |                 4 |
| Mackenzie |   2020 |                 5 |
| Mackenzie |   2021 |                 7 |
| Mackenzie |   2022 |                 5 |
| Mackenzie |   2023 |                 6 |
| Mackenzie |   2024 |                 4 |
| Ob        |   2003 |                 1 |
| Ob        |   2004 |                 7 |
| Ob        |   2005 |                 7 |
| Ob        |   2006 |                 2 |
| Ob        |   2009 |                 5 |
| Ob        |   2010 |                 5 |
| Ob        |   2011 |                 5 |
| Ob        |   2012 |                 4 |
| Ob        |   2013 |                 6 |
| Ob        |   2014 |                 6 |
| Ob        |   2015 |                 6 |
| Ob        |   2016 |                 6 |
| Ob        |   2017 |                 6 |
| Ob        |   2018 |                 6 |
| Ob        |   2019 |                 4 |
| Ob        |   2020 |                 6 |
| Ob        |   2021 |                 6 |
| Ob        |   2022 |                 6 |
| Ob        |   2023 |                 5 |
| Yenisey   |   2003 |                 1 |
| Yenisey   |   2004 |                 7 |
| Yenisey   |   2005 |                 7 |
| Yenisey   |   2006 |                 2 |
| Yenisey   |   2009 |                 5 |
| Yenisey   |   2010 |                 5 |
| Yenisey   |   2011 |                 5 |
| Yenisey   |   2012 |                 4 |
| Yenisey   |   2013 |                 6 |
| Yenisey   |   2014 |                 6 |
| Yenisey   |   2015 |                 6 |
| Yenisey   |   2016 |                 6 |
| Yenisey   |   2017 |                 6 |
| Yenisey   |   2018 |                 6 |
| Yenisey   |   2019 |                 4 |
| Yenisey   |   2020 |                 6 |
| Yenisey   |   2021 |                 6 |
| Yenisey   |   2022 |                 6 |
| Yenisey   |   2023 |                 4 |
| Yukon     |   2003 |                 1 |
| Yukon     |   2004 |                 7 |
| Yukon     |   2005 |                 7 |
| Yukon     |   2006 |                 2 |
| Yukon     |   2009 |                 5 |
| Yukon     |   2010 |                 6 |
| Yukon     |   2011 |                 5 |
| Yukon     |   2012 |                 3 |
| Yukon     |   2013 |                 5 |
| Yukon     |   2014 |                 5 |
| Yukon     |   2015 |                 6 |
| Yukon     |   2016 |                 7 |
| Yukon     |   2017 |                 5 |
| Yukon     |   2018 |                 5 |
| Yukon     |   2019 |                 6 |
| Yukon     |   2020 |                 2 |
| Yukon     |   2021 |                 6 |
| Yukon     |   2022 |                 5 |
| Yukon     |   2023 |                 6 |
| Yukon     |   2024 |                 5 |

## 5. Absorbance/CDOM Pair Counts by River
| river     |   lab_optical_rows |
|:----------|-------------------:|
| Kolyma    |                139 |
| Lena      |                141 |
| Mackenzie |                164 |
| Ob        |                142 |
| Yenisey   |                142 |
| Yukon     |                154 |

## 6. Daily Discharge Coverage
| river     | first_date   | last_date   |   n_days |   n_nonmissing |
|:----------|:-------------|:------------|---------:|---------------:|
| Kolyma    | 1978-01-01   | 2026-01-31  |    17563 |          15367 |
| Lena      | 1936-01-01   | 2026-01-17  |    32890 |          32701 |
| Mackenzie | 1972-03-21   | 2025-12-06  |    19619 |          19298 |
| Ob        | 1936-01-01   | 2025-12-10  |    32852 |          32792 |
| Yenisey   | 1936-01-01   | 2026-01-31  |    32904 |          30402 |
| Yukon     | 1975-01-01   | 2025-10-06  |    18542 |          16626 |

## 7. Hydroclimate Daily Coverage
| river     | first_date   | last_date   |   n_days |   n_nonmissing |
|:----------|:-------------|:------------|---------:|---------------:|
| Kolyma    | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Lena      | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Mackenzie | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Ob        | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Yenisey   | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Yukon     | 2000-05-01   | 2024-10-15  |     4200 |           4200 |

## 8. Optical Proxy Coverage by Sensor
| river     | sensor   |   optical_rows |
|:----------|:---------|---------------:|
| Kolyma    | HLS      |           7347 |
| Lena      | HLS      |           7380 |
| Mackenzie | HLS      |           7436 |
| Ob        | HLS      |           8164 |
| Yenisey   | HLS      |           8886 |
| Yukon     | HLS      |           7854 |

## 9. Optical Matched DOC Sample Count
| river     |   window_days |   matched_doc_samples |
|:----------|--------------:|----------------------:|
| Ob        |             0 |                    18 |
| Ob        |             1 |                    20 |
| Ob        |             3 |                    21 |
| Ob        |             7 |                    22 |
| Yenisey   |             0 |                    15 |
| Yenisey   |             1 |                    23 |
| Yenisey   |             3 |                    23 |
| Yenisey   |             7 |                    23 |
| Lena      |             0 |                    15 |
| Lena      |             1 |                    18 |
| Lena      |             3 |                    18 |
| Lena      |             7 |                    18 |
| Kolyma    |             0 |                    19 |
| Kolyma    |             1 |                    22 |
| Kolyma    |             3 |                    23 |
| Kolyma    |             7 |                    24 |
| Yukon     |             0 |                    20 |
| Yukon     |             1 |                    26 |
| Yukon     |             3 |                    28 |
| Yukon     |             7 |                    29 |
| Mackenzie |             0 |                    20 |
| Mackenzie |             1 |                    23 |
| Mackenzie |             3 |                    24 |
| Mackenzie |             7 |                    25 |

## Old Project Snapshot Breakdown
| old_project_subdir   |   file_count |
|:---------------------|-------------:|
| data/interim         |          151 |
| data/raw             |           13 |
| data/raw_external    |            2 |
| total                |          166 |

## Old Snapshot Promotable Files
| product_family   | target_canonical_table       |   file_count |
|:-----------------|:-----------------------------|-------------:|
| auxiliary        | auxiliary_context_canonical  |            2 |
| era5             | daily_hydroclimate_canonical |           14 |
| hls              | optical_timeseries_canonical |           15 |
| hydroclimate     | daily_hydroclimate_canonical |            7 |
| modis            | daily_hydroclimate_canonical |           14 |
| roi              | roi_catalog                  |           39 |
| smap             | auxiliary_context_canonical  |            7 |

## Old Snapshot Promotion Summary
| target_canonical_table       | source_id                              |   promoted_rows |
|:-----------------------------|:---------------------------------------|----------------:|
| roi_catalog                  | old_arctic_doc_snowmelt_untrained_data |              39 |
| daily_hydroclimate_canonical | old_arctic_doc_snowmelt_untrained_data |           25200 |
| optical_timeseries_canonical | old_arctic_doc_snowmelt_untrained_data |           47067 |
| auxiliary_context_canonical  | old_arctic_doc_snowmelt_untrained_data |           86324 |

## Old Snapshot Raw Duplicate/Conflict Summary
| decision                      |   file_count |
|:------------------------------|-------------:|
| duplicate_of_official_current |            7 |
| old_only_candidate            |            8 |

## Old Snapshot ROI Promotion Summary
| river     | roi_set                 |   roi_count |
|:----------|:------------------------|------------:|
| Kolyma    | auto_jrc_center_channel |           1 |
| Kolyma    | final_primary           |           1 |
| Kolyma    | final_relaxed           |           1 |
| Kolyma    | final_strict            |           1 |
| Kolyma    | initial_buffer          |           1 |
| Kolyma    | station_point           |           1 |
| Lena      | auto_jrc_center_channel |           1 |
| Lena      | final_primary           |           1 |
| Lena      | final_relaxed           |           1 |
| Lena      | final_strict            |           1 |
| Lena      | initial_buffer          |           1 |
| Lena      | station_point           |           1 |
| Mackenzie | auto_jrc_center_channel |           2 |
| Mackenzie | final_primary           |           1 |
| Mackenzie | final_relaxed           |           1 |
| Mackenzie | final_strict            |           1 |
| Mackenzie | initial_buffer          |           2 |
| Mackenzie | station_point           |           2 |
| Ob        | auto_jrc_center_channel |           1 |
| Ob        | final_primary           |           1 |
| Ob        | final_relaxed           |           1 |
| Ob        | final_strict            |           1 |
| Ob        | initial_buffer          |           1 |
| Ob        | station_point           |           1 |
| Yenisey   | auto_jrc_center_channel |           1 |
| Yenisey   | final_primary           |           1 |
| Yenisey   | final_relaxed           |           1 |
| Yenisey   | final_strict            |           1 |
| Yenisey   | initial_buffer          |           1 |
| Yenisey   | station_point           |           1 |
| Yukon     | auto_jrc_center_channel |           1 |
| Yukon     | final_primary           |           1 |
| Yukon     | final_relaxed           |           1 |
| Yukon     | final_strict            |           1 |
| Yukon     | initial_buffer          |           1 |
| Yukon     | station_point           |           1 |

## Old Snapshot Hydroclimate Promotion Summary
| river     | first_date   | last_date   |   n_days |   n_nonmissing |
|:----------|:-------------|:------------|---------:|---------------:|
| Kolyma    | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Lena      | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Mackenzie | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Ob        | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Yenisey   | 2000-05-01   | 2024-10-15  |     4200 |           4200 |
| Yukon     | 2000-05-01   | 2024-10-15  |     4200 |           4200 |

## Old Snapshot Optical Promotion Summary
| river     | sensor   |   optical_rows |
|:----------|:---------|---------------:|
| Kolyma    | HLS      |           7347 |
| Lena      | HLS      |           7380 |
| Mackenzie | HLS      |           7436 |
| Ob        | HLS      |           8164 |
| Yenisey   | HLS      |           8886 |
| Yukon     | HLS      |           7854 |

## Canonical Tables Source Composition
| canonical_table              | source_id                              |   rows |
|:-----------------------------|:---------------------------------------|-------:|
| doc_labels_canonical         | arcticgro_water_quality_current        |    595 |
| doc_labels_canonical         | old_arctic_doc_snowmelt_untrained_data |      0 |
| daily_hydroclimate_canonical | old_arctic_doc_snowmelt_untrained_data |  25200 |
| optical_timeseries_canonical | old_arctic_doc_snowmelt_untrained_data |  47067 |
| roi_catalog                  | old_arctic_doc_snowmelt_untrained_data |     39 |
| auxiliary_context_canonical  | old_arctic_doc_snowmelt_untrained_data |  86324 |

## Remaining Snapshot Files Not Promoted
| snapshot_path                                                                                                           | inferred_product_family   | not_promoted_reason                                                             |
|:------------------------------------------------------------------------------------------------------------------------|:--------------------------|:--------------------------------------------------------------------------------|
| data/raw_external/old_project_snapshot/data/raw/arcticgro/arcticgro_discharge_page.html                                 | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/arcticgro_input_template.csv                                  | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/arcticgro_parameter_description_20250402.csv                  | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/arcticgro_water_quality_20250402.csv                          | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/arcticgro_water_quality_20250402.xlsx                         | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Kolyma_Kolymskoe_Version_20260210.xlsx                        | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Kolyma_Srednekolymsk_Version_20260210.xlsx                    | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Lena_Kyusyur_Version_20260210.xlsx                            | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Mackenzie_ArcticRedRiver_Version_20260210.xlsx                | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Ob_Salekhard_Version_20260210.xlsx                            | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/README_DOWNLOAD_ARCTICGRO.md                                  | raw_arcticgro             | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Yenisei_Igarka_Version_20260210.xlsx                          | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw/arcticgro/Yukon_PilotStation_Version_20260210.xlsx                      | discharge                 | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw_external/arcticgro/absorbance/arcticgro_absorbance_20260520_212754.xlsx | raw_external_arcticgro    | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/raw_external/arcticgro/water_quality/arcticgro_water_quality_20250402.csv   | raw_external_arcticgro    | raw files require duplicate/conflict comparison, not direct canonical promotion |
| data/raw_external/old_project_snapshot/data/interim/auto_roi_qc_metrics.csv                                             | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/auto_roi_qc_metrics.csv                             | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/main_channel_corridor.geojson                       | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/roi_candidates_core.geojson                         | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/roi_candidates_exploratory.geojson                  | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/roi_candidates_relaxed.geojson                      | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/roi_core_constrained.geojson                        | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/roi_relaxed_constrained.geojson                     | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/auto_roi_qc_metrics.csv                               | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/core_rescue.geojson                                   | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/main_channel_corridor.geojson                         | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/relaxed_rescue.geojson                                | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/roi_candidates_core.geojson                           | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/roi_candidates_exploratory.geojson                    | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/roi_candidates_relaxed.geojson                        | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/roi_core_constrained.geojson                          | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/roi_relaxed_constrained.geojson                       | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/sentinel2_reflectance_final_primary.csv               | optical                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/auto_roi_qc_metrics.csv                          | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/main_channel_corridor.geojson                    | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/roi_candidates_core.geojson                      | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/roi_candidates_exploratory.geojson               | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/roi_candidates_relaxed.geojson                   | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/roi_core_constrained.geojson                     | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/roi_relaxed_constrained.geojson                  | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/auto_roi_qc_metrics.csv                                 | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/core_rescue.geojson                                     | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/main_channel_corridor.geojson                           | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/main_channel_corridor_snap_rescue.geojson               | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/roi_candidates_core.geojson                             | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/roi_candidates_exploratory.geojson                      | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/roi_candidates_relaxed.geojson                          | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/roi_core_constrained.geojson                            | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/roi_relaxed_constrained.geojson                         | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/sentinel2_reflectance_final_primary.csv                 | optical                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/trimmed_core.geojson                                    | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/auto_roi_qc_metrics.csv                            | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/core_rescue.geojson                                | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/main_channel_corridor.geojson                      | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/relaxed_rescue.geojson                             | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/roi_candidates_core.geojson                        | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/roi_candidates_exploratory.geojson                 | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/roi_candidates_relaxed.geojson                     | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/roi_core_constrained.geojson                       | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/roi_relaxed_constrained.geojson                    | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/sentinel2_reflectance_final_primary.csv            | optical                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/auto_roi_qc_metrics.csv                              | qc                        | QC file is used as sidecar evidence                                             |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/main_channel_corridor.geojson                        | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/roi_candidates_core.geojson                          | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/roi_candidates_exploratory.geojson                   | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/roi_candidates_relaxed.geojson                       | roi                       | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/roi_core_constrained.geojson                         | unknown                   | no supported canonical target                                                   |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/roi_relaxed_constrained.geojson                      | unknown                   | no supported canonical target                                                   |

## Old Snapshot Hydroclimate Unmapped Columns
| snapshot_path                                                                                                               | original_relative_path                                                               | inferred_product_family   | unmapped_columns_json                                           | notes                                                 |
|:----------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:--------------------------|:----------------------------------------------------------------|:------------------------------------------------------|
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/modis_snow_daily.csv                                    | data/interim/by_river/kolyma/modis_snow_daily.csv                                    | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/modis_snow_daily.csv                                      | data/interim/by_river/lena/modis_snow_daily.csv                                      | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/modis_snow_daily.csv                                 | data/interim/by_river/mackenzie/modis_snow_daily.csv                                 | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/modis_snow_daily.csv                                        | data/interim/by_river/ob/modis_snow_daily.csv                                        | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/modis_snow_daily.csv                                   | data/interim/by_river/yenisey/modis_snow_daily.csv                                   | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/modis_snow_daily.csv                                     | data/interim/by_river/yukon/modis_snow_daily.csv                                     | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/kolyma/modis_snow_daily_2000_2024.csv    | data/interim/longterm_hydroclimate/by_river/kolyma/modis_snow_daily_2000_2024.csv    | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/lena/modis_snow_daily_2000_2024.csv      | data/interim/longterm_hydroclimate/by_river/lena/modis_snow_daily_2000_2024.csv      | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/mackenzie/modis_snow_daily_2000_2024.csv | data/interim/longterm_hydroclimate/by_river/mackenzie/modis_snow_daily_2000_2024.csv | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/ob/modis_snow_daily_2000_2024.csv        | data/interim/longterm_hydroclimate/by_river/ob/modis_snow_daily_2000_2024.csv        | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/yenisey/modis_snow_daily_2000_2024.csv   | data/interim/longterm_hydroclimate/by_river/yenisey/modis_snow_daily_2000_2024.csv   | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/yukon/modis_snow_daily_2000_2024.csv     | data/interim/longterm_hydroclimate/by_river/yukon/modis_snow_daily_2000_2024.csv     | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/modis_snow_daily.csv                                                    | data/interim/modis_snow_daily.csv                                                    | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/modis_snow_daily_template.csv                                           | data/interim/modis_snow_daily_template.csv                                           | modis                     | ["mean_ndsi_snow_cover", "valid_modis_pixels"]                  | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/era5_land_daily.csv                                     | data/interim/by_river/kolyma/era5_land_daily.csv                                     | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/era5_land_daily.csv                                       | data/interim/by_river/lena/era5_land_daily.csv                                       | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/era5_land_daily.csv                                  | data/interim/by_river/mackenzie/era5_land_daily.csv                                  | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/era5_land_daily.csv                                         | data/interim/by_river/ob/era5_land_daily.csv                                         | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/era5_land_daily.csv                                    | data/interim/by_river/yenisey/era5_land_daily.csv                                    | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/era5_land_daily.csv                                      | data/interim/by_river/yukon/era5_land_daily.csv                                      | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/era5_land_daily.csv                                                     | data/interim/era5_land_daily.csv                                                     | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/era5_land_daily_template.csv                                            | data/interim/era5_land_daily_template.csv                                            | era5                      | ["temp2m_mean_K"]                                               | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/kolyma/era5_land_daily_2000_2024.csv     | data/interim/longterm_hydroclimate/by_river/kolyma/era5_land_daily_2000_2024.csv     | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/lena/era5_land_daily_2000_2024.csv       | data/interim/longterm_hydroclimate/by_river/lena/era5_land_daily_2000_2024.csv       | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/mackenzie/era5_land_daily_2000_2024.csv  | data/interim/longterm_hydroclimate/by_river/mackenzie/era5_land_daily_2000_2024.csv  | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/ob/era5_land_daily_2000_2024.csv         | data/interim/longterm_hydroclimate/by_river/ob/era5_land_daily_2000_2024.csv         | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/yenisey/era5_land_daily_2000_2024.csv    | data/interim/longterm_hydroclimate/by_river/yenisey/era5_land_daily_2000_2024.csv    | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/longterm_hydroclimate/by_river/yukon/era5_land_daily_2000_2024.csv      | data/interim/longterm_hydroclimate/by_river/yukon/era5_land_daily_2000_2024.csv      | era5                      | ["temp2m_mean_K", "snowmelt_total_m"]                           | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/kolyma/daily_hydroclimate_features.csv                         | data/interim/by_river/kolyma/daily_hydroclimate_features.csv                         | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/lena/daily_hydroclimate_features.csv                           | data/interim/by_river/lena/daily_hydroclimate_features.csv                           | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/mackenzie/daily_hydroclimate_features.csv                      | data/interim/by_river/mackenzie/daily_hydroclimate_features.csv                      | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/ob/daily_hydroclimate_features.csv                             | data/interim/by_river/ob/daily_hydroclimate_features.csv                             | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yenisey/daily_hydroclimate_features.csv                        | data/interim/by_river/yenisey/daily_hydroclimate_features.csv                        | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/by_river/yukon/daily_hydroclimate_features.csv                          | data/interim/by_river/yukon/daily_hydroclimate_features.csv                          | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |
| data/raw_external/old_project_snapshot/data/interim/daily_hydroclimate_features.csv                                         | data/interim/daily_hydroclimate_features.csv                                         | hydroclimate              | ["temp2m_mean_K", "mean_ndsi_snow_cover", "valid_modis_pixels"] | columns retained outside daily_hydroclimate_canonical |

## 10. Duplicate Statistics and Rules
Deduplication groups records by river, station, date, parameter, and sample id when available. Preference order is official ArcticGRO current, accepted/non-flagged records, explicit DOC, complete coordinates, and newest version.

| is_duplicate   | preferred_record   |   records |
|:---------------|:-------------------|----------:|
| False          | True               |       595 |

## 11. Unavailable Records and Exclusion Reasons
| river     | exclusion_reason             |   records |
|:----------|:-----------------------------|----------:|
| Kolyma    | missing_or_non_numeric_value |        11 |
| Kolyma    | nan                          |        87 |
| Lena      | missing_or_non_numeric_value |        11 |
| Lena      | nan                          |        87 |
| Mackenzie | nan                          |       103 |
| Ob        | missing_or_non_numeric_value |        12 |
| Ob        | nan                          |        87 |
| Yenisey   | missing_or_non_numeric_value |        11 |
| Yenisey   | nan                          |        87 |
| Yukon     | missing_or_non_numeric_value |         3 |
| Yukon     | nan                          |        96 |

## 12. Future Training Recommendations
- Recommended main training set: `training_matrix_daily_predictable.csv`, daily-predictable features only.
- Recommended supplementary validation: `lab_optical_proxy_canonical.csv` for absorbance/CDOM mechanism checks.
- Recommended optical sensitivity: HLS/Sentinel-2/Landsat matched subsets once `optical_timeseries_canonical.csv` is populated.

## 13. Explicit Warnings
- Do not use lab absorbance as production daily predictor.
- Do not treat satellite reflectance as direct DOC observation.
- Do not treat six-river domain as full Arctic Ocean DOC budget.
- Do not silently merge TOC with DOC.

## Generated Tables
- Training matrix rows: 547