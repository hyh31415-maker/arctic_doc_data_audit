from __future__ import annotations

import pandas as pd

from ..normalize import load_rivers
from ..paths import PROCESSED_DIR
from ..schemas import ensure_columns, write_table


def run() -> pd.DataFrame:
    rows = []
    for river in load_rivers():
        rows.append(
            {
                "river": river,
                "basin_id": "",
                "geometry_source": "",
                "upstream_area_km2": pd.NA,
                "pfaf_id": "",
                "attribute_source": "",
                "hydroatlas_attributes_json": "{}",
                "landcover_attributes_json": "{}",
                "climate_aggregation_notes": "HydroBASINS/HydroATLAS local files not yet configured.",
                "source_id": "hydrobasins;hydroatlas",
                "quality_flag": "placeholder_only",
                "notes": "Basin context placeholder; not a DOC label.",
            }
        )
    frame = ensure_columns(pd.DataFrame(rows), "basin_context_canonical")
    write_table(frame, "basin_context_canonical", PROCESSED_DIR / "basin_context_canonical.csv")
    roi_rows = []
    for river, meta in load_rivers().items():
        roi_paths = meta.get("roi_paths") or {}
        if not roi_paths:
            roi_rows.append(
                {
                    "river": river,
                    "roi_set": "not_configured",
                    "roi_path": "",
                    "roi_exists": False,
                    "roi_area_m2": pd.NA,
                    "roi_source": "",
                    "roi_risk": "manual_review_required",
                    "manual_review_required": True,
                    "notes": "No ROI path configured yet.",
                }
            )
            continue
        for roi_set, roi_path in roi_paths.items():
            roi_rows.append(
                {
                    "river": river,
                    "roi_set": roi_set,
                    "roi_path": roi_path,
                    "roi_exists": pd.notna(roi_path),
                    "roi_area_m2": pd.NA,
                    "roi_source": "configs/rivers.yaml",
                    "roi_risk": "unverified",
                    "manual_review_required": True,
                    "notes": "ROI path requires geometry QA before GEE extraction.",
                }
            )
    roi_path = PROCESSED_DIR / "roi_catalog.csv"
    if roi_path.exists():
        existing = pd.read_csv(roi_path)
        if not existing.empty and "source_id" in existing.columns and existing["source_id"].astype(str).str.contains("old_arctic_doc_snowmelt_untrained_data", na=False).any():
            write_table(ensure_columns(existing, "roi_catalog"), "roi_catalog", roi_path)
            return frame
    write_table(ensure_columns(pd.DataFrame(roi_rows), "roi_catalog"), "roi_catalog", roi_path)
    return frame
