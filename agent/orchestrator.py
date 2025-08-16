# agent/orchestrator.py
from __future__ import annotations
from typing import Dict, Any, List
import os
import pandas as pd

from matching.engine import (
    UserProfile,
    load_catalog,
    rank_cars,
)

def _to_float_or_none(val: Any) -> float | None:
    if val in [None, "", "null"]:
        return None
    try:
        return float(val)
    except Exception:
        return None

def _to_int_or_default(val: Any, default: int) -> int:
    try:
        v = int(val)
        return v if v > 0 else default
    except Exception:
        return default

def _normalize_fuel_type(raw: Any) -> str:
    if raw is None:
        return "any"
    s = str(raw).strip().lower()
    fuel_map = {
        "": "any",
        "any": "any",
        "gas": "gas",
        "gasoline": "gas",
        "petrol": "gas",
        "diesel": "diesel",
        "hybrid": "hybrid",
        "hev": "hybrid",
        "phev": "phev",
        "plug-in": "phev",
        "plugin": "phev",
        "ev": "bev",
        "bev": "bev",
        "electric": "bev",
        "battery": "bev",
    }
    return fuel_map.get(s, s)

def _detect_catalog_path(explicit: str | None = None) -> str | None:
    candidates = [
        explicit,
        os.getenv("CARMATCH_US_CATALOG"),
        "data/catalog_us.parquet",
        "catalog_us.parquet",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

def get_recommendations(answers: Dict[str, Any], catalog_path: str | None = None) -> Dict[str, Any]:
    # 1) טעינת קטלוג
    path = _detect_catalog_path(catalog_path)
    catalog = load_catalog(path)

    # 2) בניית פרופיל
    budget = _to_float_or_none(answers.get("budget_usd", None))
    profile = UserProfile(
        new_or_used=answers.get("condition", "any"),
        usage=answers.get("usage", "mixed"),
        passengers=_to_int_or_default(answers.get("passengers", 4) or 4, 4),
        annual_km=_to_int_or_default(answers.get("annual_km", 12000) or 12000, 12000),
        terrain=answers.get("terrain", "flat"),
        budget=budget,
        prioritize_mpg=bool(answers.get("prioritize_mpg", True)),
        prioritize_safety=bool(answers.get("prioritize_safety", True)),
        prioritize_space=bool(answers.get("prioritize_space", False)),
        weights=answers.get("weights", {}) or {},
    )

    # 3) פרמטרים משלימים
    fuel_type = _normalize_fuel_type(answers.get("fuel_type", "any"))
    top_n = _to_int_or_default(answers.get("top_n", 10), 10)
    min_mpg = answers.get("min_mpg", None)
    min_mpg = _to_float_or_none(min_mpg) if min_mpg is not None else None
    max_per_model = _to_int_or_default(answers.get("max_per_model", 1), 1)
    try:
        max_share_per_fuel = float(answers.get("max_share_per_fuel", 0.7))
    except Exception:
        max_share_per_fuel = 0.7

    # 4) דירוג
    ranked_df: pd.DataFrame = rank_cars(
        profile=profile,
        catalog=catalog,
        top_n=top_n,
        min_mpg=min_mpg,
        max_per_model=max_per_model,
        max_share_per_fuel=max_share_per_fuel,
        fuel_type=fuel_type,
    )

    # 5) פורמט ל-UI
    wanted_cols = [
        "make","model","option_text","VClass","fuelType",
        "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
        "price_best","price_source","annual_fuel_cost","score","reasons"
    ]
    cols = [c for c in wanted_cols if c in ranked_df.columns]
    items: List[Dict[str, Any]] = []
    for _, row in ranked_df[cols].iterrows():
        item: Dict[str, Any] = {k: row.get(k, None) for k in cols}
        if item.get("score") is not None:
            try:
                item["score"] = round(float(item["score"]), 3)
            except Exception:
                pass
        if item.get("price_best") is not None:
            try:
                price_num = float(item["price_best"])
                item["price_best_num"] = int(round(price_num))
                item["price_best"] = f"${item['price_best_num']:,}"
            except Exception:
                pass
        if item.get("annual_fuel_cost") is not None:
            try:
                afc_num = float(item["annual_fuel_cost"])
                item["annual_fuel_cost"] = f"${int(round(afc_num)):,}"
            except Exception:
                pass
        items.append(item)

    return {
        "profile": profile.__dict__,
        "count": len(items),
        "results": items,
    }