from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.preprocess.doc_labels import canonicalize_doc_labels
from arctic_doc_data_audit.schemas import required_columns


def _raw_row(parameter: str, value: float = 5.0) -> dict[str, object]:
    return {
        "source_id": "arcticgro_water_quality_current",
        "source_file": "data/raw/arcticgro/water_quality/test.xlsx",
        "source_sheet": "Yukon",
        "source_row": 11,
        "raw_river": "Yukon",
        "raw_station": "Pilot Station",
        "raw_date": "2020-06-01",
        "raw_parameter": parameter,
        "raw_value": value,
        "raw_unit": "mg/L",
        "raw_flag": "AV",
        "raw_method": "test",
        "raw_medium": "water",
        "raw_fraction": "dissolved",
        "raw_latitude": 61.93,
        "raw_longitude": -162.88,
        "raw_sample_id": "sample-1",
        "notes": "dataset_version=20250101",
    }


def test_doc_label_canonical_schema() -> None:
    frame, _ = canonicalize_doc_labels(pd.DataFrame([_raw_row("DOC")]))
    for column in required_columns("doc_labels_canonical"):
        assert column in frame.columns
    assert frame.loc[0, "parameter_canonical"] == "DOC"
    assert frame.loc[0, "value_mgC_L"] == 5.0


def test_toc_cannot_silently_become_doc() -> None:
    frame, _ = canonicalize_doc_labels(pd.DataFrame([_raw_row("TOC")]))
    assert frame.loc[0, "parameter_canonical"] == "TOC"
    assert bool(frame.loc[0, "is_toc_not_doc"])
    assert not bool(frame.loc[0, "can_train_doc_model"])
    assert "TOC_retained_separately_not_DOC" in frame.loc[0, "exclusion_reason"]

