# agent/orchestrator.py
from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd

from matching.engine import (
    UserProfile,
    load_catalog,
    rank_cars,
)

def get_recommendations(answers: Dict[str, Any], catalog_path: str | None = None) -> Dict[str, Any]:
    """
    ממיר תשובות משתמש לפרופיל, טוען קטלוג, מריץ דירוג ומחזיר Top-N בפורמט פשוט ל-UI.
    """
    # 1) טעינת קטלוג (ברירת מחדל: data/catalog_us.parquet או מהסביבה)
    catalog = load_catalog(catalog_path)

    # 2) בניית פרופיל מהתשובות
    profile = UserProfile(
        new_or_used=answers.get("condition", "any"),
        usage=answers.get("usage", "mixed"),
        passengers=int(answers.get("passengers", 4) or 4),
        annual_km=int(answers.get("annual_km", 12000) or 12000),
        terrain=answers.get("terrain", "flat"),
        budget=answers.get("budget_usd", None),  # יכול להיות None
        prioritize_mpg=bool(answers.get("prioritize_mpg", True)),
        prioritize_safety=bool(answers.get("prioritize_safety", True)),
        prioritize_space=bool(answers.get("prioritize_space", False)),
        weights=answers.get("weights", {}) or {},
    )

    # 3) פרמטרים משלימים
    fuel_type = (answers.get("fuel_type") or "any").lower()  # "any"/"gas"/"phev"/"bev"
    top_n = int(answers.get("top_n", 10))
    min_mpg = answers.get("min_mpg", None)
    if min_mpg is not None:
        try:
            min_mpg = float(min_mpg)
        except Exception:
            min_mpg = None

    # 4) הרצת המנוע
    ranked_df: pd.DataFrame = rank_cars(
        profile=profile,
        catalog=catalog,
        top_n=top_n,
        min_mpg=min_mpg,
        max_per_model=int(answers.get("max_per_model", 1)),
        max_share_per_fuel=float(answers.get("max_share_per_fuel", 0.7)),
        fuel_type=fuel_type,
    )

    # 5) פורמט ידידותי ל-UI
    cols = [c for c in [
        "make","model","option_text","VClass","fuelType",
        "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
        "price_best","price_source","annual_fuel_cost","score","reasons"
    ] if c in ranked_df.columns]

    items: List[Dict[str, Any]] = []
    for _, row in ranked_df[cols].iterrows():
        item = {k: row[k] for k in cols}
        # עיצוב קל: מחירים כטקסט, סקורים עגולים
        if "score" in item and item["score"] is not None:
            item["score"] = round(float(item["score"]), 3)
        if "price_best" in item and item["price_best"] is not None:
            try:
                item["price_best"] = f"${int(round(float(item['price_best']))):,}"
            except Exception:
                pass
        if "annual_fuel_cost" in item and item["annual_fuel_cost"] is not None:
            try:
                item["annual_fuel_cost"] = f"${int(round(float(item['annual_fuel_cost']))):,}"
            except Exception:
                pass
        items.append(item)

    return {
        "profile": profile.__dict__,
        "count": len(items),
        "results": items,
    }
