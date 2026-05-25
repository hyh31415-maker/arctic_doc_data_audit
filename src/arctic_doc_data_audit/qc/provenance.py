from __future__ import annotations

import pandas as pd


def rows_missing_provenance(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    provenance_columns = [column for column in ["source_id", "notes", "source_file"] if column in frame.columns]
    if not provenance_columns:
        return frame
    mask = pd.Series(False, index=frame.index)
    for column in provenance_columns:
        mask |= frame[column].isna() | (frame[column].astype(str).str.strip() == "")
    return frame[mask]

