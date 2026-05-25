from __future__ import annotations

import pandas as pd

from arctic_doc_data_audit.deduplicate import apply_deduplication


def test_duplicate_records_grouped_and_one_preferred() -> None:
    rows = [
        {
            "label_id": "a",
            "source_id": "wqp_usgs_yukon_candidate",
            "river": "Yukon",
            "station": "Pilot Station",
            "date": "2020-06-01",
            "parameter_canonical": "DOC",
            "sample_id": "s1",
            "quality_flag": "PV",
            "dataset_version": "20200101",
            "latitude": 61.9,
            "longitude": -162.8,
        },
        {
            "label_id": "b",
            "source_id": "arcticgro_water_quality_current",
            "river": "Yukon",
            "station": "Pilot Station",
            "date": "2020-06-01",
            "parameter_canonical": "DOC",
            "sample_id": "s1",
            "quality_flag": "AV",
            "dataset_version": "20250101",
            "latitude": 61.9,
            "longitude": -162.8,
        },
    ]
    out, decisions = apply_deduplication(pd.DataFrame(rows))
    assert out["is_duplicate"].all()
    assert out["preferred_record"].sum() == 1
    assert out.loc[out["preferred_record"], "label_id"].iloc[0] == "b"
    assert len(decisions) == 1

