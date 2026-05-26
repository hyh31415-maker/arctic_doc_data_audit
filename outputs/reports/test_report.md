# Test Report

Generated: 2026-05-26

No DOC model training was run.

## Commands

```powershell
python -m arctic_doc_data_audit.cli promote-old-snapshot --all
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli report
python -m arctic_doc_data_audit.cli model-readiness
python -m pytest
```

## Result

```text
25 passed in 20.01s
```

## Data-Layer Checks

- Sentinel-2 legacy snapshot rows were promoted to `optical_timeseries_canonical.csv`, not DOC labels.
- `temp2m_mean_K` is converted to `temperature_2m_C` using `K - 273.15`.
- `snowmelt_total_m` is mapped to `snowmelt_m`.
- `mean_ndsi_snow_cover` and `valid_modis_pixels` are retained in the hydroclimate sidecar/QC table.
- `training_matrix_daily_predictable.csv` still excludes lab absorbance/CDOM columns.
- `model-readiness` generates readiness tables and report without training a model.
