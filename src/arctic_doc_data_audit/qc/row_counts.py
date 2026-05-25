from __future__ import annotations

import pandas as pd


def count_by_river(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "river" not in frame.columns:
        return pd.DataFrame(columns=["river", "rows"])
    return frame.groupby("river", dropna=False).size().reset_index(name="rows")

