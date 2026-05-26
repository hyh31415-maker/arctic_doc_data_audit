from __future__ import annotations

import pandas as pd

from ..paths import PROCESSED_DIR
from ..schemas import ensure_columns, write_table


def run() -> pd.DataFrame:
    existing = PROCESSED_DIR / "daily_hydroclimate_canonical.csv"
    if existing.exists():
        frame = pd.read_csv(existing)
        if not frame.empty:
            write_table(ensure_columns(frame, "daily_hydroclimate_canonical"), "daily_hydroclimate_canonical", existing)
            return ensure_columns(frame, "daily_hydroclimate_canonical")
    frame = ensure_columns(pd.DataFrame(), "daily_hydroclimate_canonical")
    write_table(frame, "daily_hydroclimate_canonical", PROCESSED_DIR / "daily_hydroclimate_canonical.csv")
    return frame
