from __future__ import annotations

import pandas as pd

from ..paths import PROCESSED_DIR
from ..schemas import ensure_columns, write_table


def run() -> pd.DataFrame:
    existing = PROCESSED_DIR / "optical_timeseries_canonical.csv"
    if existing.exists():
        frame = pd.read_csv(existing)
        if not frame.empty:
            write_table(ensure_columns(frame, "optical_timeseries_canonical"), "optical_timeseries_canonical", existing)
            return ensure_columns(frame, "optical_timeseries_canonical")
    frame = ensure_columns(pd.DataFrame(), "optical_timeseries_canonical")
    write_table(frame, "optical_timeseries_canonical", PROCESSED_DIR / "optical_timeseries_canonical.csv")
    return frame
