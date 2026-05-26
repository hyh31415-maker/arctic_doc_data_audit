# Fatal Data Bug Policy

Generated: 2026-05-26T20:27:02Z

No DOC model was trained. No DOC prediction was generated. No flux was generated.

## Fatal Data Bugs

If found, open a new freeze version:

- DOC unit conversion error
- DOC/TOC confusion
- duplicate/preferred label error
- wrong discharge station or unit
- GEE band scaling/mapping error
- station-to-basin catastrophic mismatch
- HydroATLAS aggregation error
- lab optical leakage into daily production predictors
- raw file corrupt/partial
- freeze hash mismatch

## Non-Fatal Issues

Do not reopen this freeze for:

- optional new external source discovered
- additional WQP/DataStream/MDPI candidate rows
- extra optical sensitivity window desired
- additional optional SMAP features
- alternative model feature engineering
- model performance poor

Non-fatal items go to `vNext` or sensitivity appendix, not the current gold freeze.
