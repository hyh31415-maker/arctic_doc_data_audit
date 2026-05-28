# Frozen Repository Handoff

- freeze_id: `data_freeze_gold_20260526_v1`
- tag_name: `data_freeze_gold_20260526_v1`
- repository_role: Frozen Data Repository
- gold_tables_location: `data/processed/gold/`
- local_backup_location: `backups/data_freeze_gold_20260526_v1/`
- hash_manifest_location: `outputs/tables/gold/gold_freeze_archive_manifest.csv`
- original_gold_table_hashes: `outputs/tables/gold/gold_table_hashes.csv`
- fatal_data_bug_policy: `outputs/reports/gold/fatal_data_bug_policy.md`

## Future Modeling Repository Recommendation

Create a clean modeling repository that treats this repository as a frozen data source. Future modeling code should read only `data/processed/gold/*` from this freeze and should keep model outputs outside this data repository.

## What Not To Modify

- Do not use raw/interim/canonical tables directly in modeling.
- Do not use old project snapshot directly.
- Do not modify gold tables during modeling.
- Do not train DOC models in this repository.
- Do not generate DOC prediction or flux products in this repository.
- If a fatal data bug is found, create a new freeze version instead of silently editing this freeze.

## How To Verify Local Gold Tables

```powershell
python -m arctic_doc_data_audit.cli archive-gold-freeze --freeze-id data_freeze_gold_20260526_v1
python -m pytest tests/test_gold_freeze.py
```

The archive manifest records SHA256 values for the local gold CSVs. The gold CSV files remain local processed artifacts and are not committed to Git.
