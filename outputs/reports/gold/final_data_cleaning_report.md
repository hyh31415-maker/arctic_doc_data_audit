# Final Data Cleaning Report

Generated: 2026-05-26T20:27:01Z

No DOC model was trained. No DOC prediction was generated. No flux was generated.

## QA Issues
| issue_id     | severity   | table_name                  | column_name      | river   | date   | issue_type       | description                                          | blocking_for_gold_freeze   | blocking_for_modeling   | recommended_action                              | resolution_status     | notes                                                                               |
|:-------------|:-----------|:----------------------------|:-----------------|:--------|:-------|:-----------------|:-----------------------------------------------------|:---------------------------|:------------------------|:------------------------------------------------|:----------------------|:------------------------------------------------------------------------------------|
| GOLD-QA-0001 | low        | daily_hydroclimate_gold.csv | snowmelt_m       |         |        | range_check_flag | 137 rows are outside the configured screening range. | False                      | False                   | Track as non-fatal QA note or sensitivity item. | accepted_non_blocking | Flagged for review; not a gold freeze blocker unless confirmed as a fatal data bug. |
| GOLD-QA-0002 | low        | daily_hydroclimate_gold.csv | surface_runoff_m |         |        | range_check_flag | 71 rows are outside the configured screening range.  | False                      | False                   | Track as non-fatal QA note or sensitivity item. | accepted_non_blocking | Flagged for review; not a gold freeze blocker unless confirmed as a fatal data bug. |

## Null Rates
See `outputs/tables/gold/final_null_rate_by_table.csv`.

## Range Checks
| table_name                  | column_name              |   checked_rows |   out_of_range_rows |   min_allowed |   max_allowed |     min_value |     max_value |
|:----------------------------|:-------------------------|---------------:|--------------------:|--------------:|--------------:|--------------:|--------------:|
| doc_labels_gold.csv         | value_mgC_L              |            547 |                   0 |             0 |           200 |   2.1         |     23.5      |
| daily_discharge_gold.csv    | Q_m3s                    |         147186 |                   0 |             0 |           nan |  19.6         | 215000        |
| daily_hydroclimate_gold.csv | temperature_2m_C         |          51685 |                   0 |           -80 |            50 | -54.2791      |     27.691    |
| daily_hydroclimate_gold.csv | positive_degree_day_Cday |          51685 |                   0 |             0 |           nan |   0           |     27.691    |
| daily_hydroclimate_gold.csv | snow_cover_fraction      |          33677 |                   0 |             0 |             1 |   0           |      1        |
| daily_hydroclimate_gold.csv | snowmelt_m               |          51685 |                 137 |             0 |           nan |  -3.72529e-09 |      1.11402  |
| daily_hydroclimate_gold.csv | surface_runoff_m         |          51685 |                  71 |             0 |           nan |  -2.98023e-08 |      0.931917 |
| optical_timeseries_gold.csv | pct_valid_water_pixels   |          94991 |                   0 |             0 |             1 |   0           |      1        |