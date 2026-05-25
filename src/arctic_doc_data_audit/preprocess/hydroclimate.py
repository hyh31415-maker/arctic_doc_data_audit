from __future__ import annotations

import pandas as pd

from ..paths import PROCESSED_DIR
from ..schemas import ensure_columns, write_table


def run() -> pd.DataFrame:
    frame = ensure_columns(pd.DataFrame(), "daily_hydroclimate_canonical")
    write_table(frame, "daily_hydroclimate_canonical", PROCESSED_DIR / "daily_hydroclimate_canonical.csv")
    return frame

