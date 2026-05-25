from __future__ import annotations

from arctic_doc_data_audit.schemas import empty_table, load_schema_config


def test_all_canonical_outputs_contain_required_columns() -> None:
    for table_name in load_schema_config()["tables"]:
        frame = empty_table(table_name)
        required = load_schema_config()["tables"][table_name]["required_columns"]
        assert all(column in frame.columns for column in required)

