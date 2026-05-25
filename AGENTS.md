# Project Conventions

This repository is a clean data-layer rebuild for Arctic river DOC / CDOM / discharge / optical proxy / hydroclimate integration.

## Scope

- Do not train DOC models in this repository.
- Do not generate final scientific conclusions here.
- Keep data roles separate:
  - DOC/TOC labels.
  - Daily-predictable predictors.
  - Laboratory absorbance/CDOM proxy.
  - Satellite optical proxy.
  - Basin context.
  - Literature and benchmark products.

## Data Rules

- Raw, external raw, interim, and processed data are generated artifacts and must stay out of git.
- Commit code, configuration, schemas, manifests, report templates/reports, and small tests only.
- Every downloaded file must have a `file_manifest.csv` row with source, URLs, retrieval time, local path, file size, SHA256, version, status, citation, and `commit_raw_data=false`.
- Failed downloads must not crash the full audit. Record failure status and next manual action in manifest and reports.
- Every canonical row must retain provenance sufficient to trace source id, file, sheet/row when applicable, version, and retrieval context.
- TOC is not DOC. Preserve TOC as a separate flagged label or sensitivity-only candidate.
- Laboratory absorbance/CDOM defaults to validation-only and must not enter `training_matrix_daily_predictable.csv`.
- Satellite reflectance is an optical proxy and must not become a DOC label.

## Reproducibility

- Python 3.11+.
- Prefer idempotent commands that can be re-run after interruption.
- Keep URLs and source IDs in `configs/sources.yaml`; do not hard-code source URLs in business logic except derived export URLs from configured/discovered URLs.
- Prefer official source pages and resolved URLs over secondary links.
- If Earth Engine is not authenticated, use dry-run/report-only mode and record the missing authentication in manifest.

## Expected Workflow

```powershell
python -m pip install -e .[test]
python -m arctic_doc_data_audit.cli init
python -m arctic_doc_data_audit.cli download --source arcticgro
python -m arctic_doc_data_audit.cli preprocess --all
python -m arctic_doc_data_audit.cli build-training-matrix
python -m arctic_doc_data_audit.cli report
python -m pytest
```

## GitHub Sync

- Review `git status --ignored` before commits.
- Never force-add files under `data/raw`, `data/raw_external`, `data/interim`, or `data/processed`.
- Manifests and Markdown reports may be committed when paths are relative and no sensitive data are present.

