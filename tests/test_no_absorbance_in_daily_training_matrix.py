from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.preprocess.training_matrix import FORBIDDEN
from arctic_doc_data_audit.qc.checks import assert_no_lab_optical_leakage
from arctic_doc_data_audit.schemas import empty_table


def test_training_matrix_schema_excludes_lab_absorbance() -> None:
    matrix = empty_table("training_matrix_daily_predictable")
    assert not FORBIDDEN.intersection(matrix.columns)
    assert_no_lab_optical_leakage(matrix)


def test_leakage_check_fails_on_absorbance_column() -> None:
    try:
        assert_no_lab_optical_leakage(pd.DataFrame(columns=["label_id", "A254"]))
    except AssertionError as exc:
        assert "A254" in str(exc)
    else:
        raise AssertionError("Expected leakage check to fail")

