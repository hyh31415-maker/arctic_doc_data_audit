from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd


def _norm(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def make_duplicate_key(row: pd.Series) -> str:
    sample_id = _norm(row.get("sample_id"))
    if sample_id:
        parts = [row.get("river"), row.get("station"), row.get("date"), row.get("parameter_canonical"), sample_id]
    else:
        rounded = row.get("value_mgC_L")
        try:
            rounded = f"{float(rounded):.6g}"
        except Exception:
            rounded = ""
        parts = [row.get("river"), row.get("station"), row.get("date"), row.get("parameter_canonical"), rounded]
    text = "|".join(_norm(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def preference_score(row: pd.Series) -> tuple[int, int, int, int, int]:
    source = _norm(row.get("source_id"))
    quality = _norm(row.get("quality_flag"))
    parameter = _norm(row.get("parameter_canonical"))
    version = "".join(ch for ch in str(row.get("dataset_version", "")) if ch.isdigit())
    try:
        version_int = int(version or 0)
    except ValueError:
        version_int = 0
    return (
        1 if source == "arcticgro_water_quality_current" else 0,
        1 if quality in {"av", ""} else 0,
        1 if parameter == "doc" else 0,
        1 if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")) else 0,
        version_int,
    )


def apply_deduplication(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame.empty:
        frame = frame.copy()
        frame["is_duplicate"] = pd.Series(dtype=bool)
        frame["duplicate_group_id"] = pd.Series(dtype=str)
        frame["preferred_record"] = pd.Series(dtype=bool)
        return frame, pd.DataFrame(columns=["duplicate_group_id", "n_records", "preferred_label_id", "decision_rule"])

    out = frame.copy()
    out["duplicate_group_id"] = out.apply(make_duplicate_key, axis=1)
    counts = out.groupby("duplicate_group_id")["duplicate_group_id"].transform("size")
    out["is_duplicate"] = counts > 1
    out["preferred_record"] = False
    decisions: list[dict[str, Any]] = []
    for group_id, group in out.groupby("duplicate_group_id", dropna=False):
        if len(group) == 1:
            out.loc[group.index, "preferred_record"] = True
            continue
        scores = group.apply(preference_score, axis=1)
        preferred_index = sorted(zip(group.index, scores), key=lambda item: item[1], reverse=True)[0][0]
        out.loc[preferred_index, "preferred_record"] = True
        decisions.append(
            {
                "duplicate_group_id": group_id,
                "n_records": len(group),
                "preferred_label_id": out.loc[preferred_index, "label_id"],
                "decision_rule": "Prefer official ArcticGRO current, accepted flag, explicit DOC, complete coordinates, newest version.",
            }
        )
    return out, pd.DataFrame(decisions)

