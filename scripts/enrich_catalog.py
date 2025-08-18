# scripts/enrich_catalog.py
from __future__ import annotations
import argparse, os, sys, time, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# מאפשר יבוא מהפרויקט (services/*)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# === APIs you already have ===
try:
    from services.nhtsa import NhtsaSafety, NhtsaRecalls  # אם אצלך השמות שונים, עדכן פה
except Exception:
    # גיבוי: אם זה מפורק לקבצים נפרדים (כמו ששלחת), ננסה לייבא כל מודול
    from services import nhtsa_safety as _nhtsa_safety  # type: ignore
    from services import nhtsa_recalls as _nhtsa_recalls  # type: ignore
    NhtsaSafety = getattr(_nhtsa_safety, "NhtsaSafety")
    NhtsaRecalls = getattr(_nhtsa_recalls, "NhtsaRecalls")

# ---------- Helpers ----------
def _is_puppeteer_source(src: Optional[str]) -> bool:
    if not src:
        return False
    return str(src).startswith("puppeteer")

def _safe_int(x) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None

def _parse_overall_rating(val: str | None) -> Optional[float]:
    """
    NHTSA מחזירה OverallRating כמחרוזת ("5", "4", "Not Rated").
    נמפה ל-float או None.
    """
    if not val:
        return None
    s = str(val).strip()
    if s.lower().startswith("not rated") or s == "0":
        return None
    try:
        return float(s)
    except Exception:
        return None

def _nhtsa_pick_best_variant(variants: list[dict]) -> Optional[dict]:
    """
    מקבל את רשימת הווריאנטים (VehicleDescription/OverallRating וכו'),
    ובוחר את זה עם דירוג כולל מקסימלי. אם אין — נחזיר None.
    """
    best = None
    best_score = -math.inf
    for v in variants or []:
        score = _parse_overall_rating(v.get("OverallRating"))
        if score is None:
            continue
        if score > best_score:
            best = v
            best_score = score
    return best

def _title(s: str | None) -> str:
    if not s:
        return ""
    # Title-case פשוט; NHTSA רגישת-רישיות חלקית
    return str(s).strip().title()

def _nhtsa_safety_for(apis: Tuple[NhtsaSafety, NhtsaRecalls], year: int, make: str, model: str) -> Tuple[Optional[float], Optional[str], Optional[int], Optional[int]]:
    """
    מחזיר: (safety_overall, safety_source_date, recalls_count, complaints_count)
    """
    nhtsa_safety, nhtsa_recalls = apis
    make_q = _title(make)
    model_q = _title(model)

    # 1) SAFETY
    safety_score: Optional[float] = None
    safety_date: Optional[str] = None
    try:
        # שלב 1: וריאנטים זמינים
        variants = nhtsa_safety.variants(year, make_q, model_q) or []
        pick = _nhtsa_pick_best_variant(variants)
        safety_score = _parse_overall_rating(pick.get("OverallRating") if pick else None)
        # תאריך עדכניות: עכשיו (כחיווי מתי שלפנו)
        safety_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        # לא מפיל את התהליך
        safety_score = None
        safety_date = None

    # 2) RECALLS & COMPLAINTS
    recalls_count: Optional[int] = None
    complaints_count: Optional[int] = None
    try:
        rec = nhtsa_recalls.recalls(make_q, model_q, year) or {}
        recalls = rec.get("results") or rec.get("Results") or rec.get("results", [])
        recalls_count = _safe_int(len(recalls))
    except Exception:
        recalls_count = None

    try:
        comp = nhtsa_recalls.complaints(make_q, model_q, year) or {}
        complaints = comp.get("results") or comp.get("Results") or comp.get("results", [])
        complaints_count = _safe_int(len(complaints))
    except Exception:
        complaints_count = None

    return safety_score, safety_date, recalls_count, complaints_count

# ---------- Main enrich ----------
def enrich_catalog(
    catalog_in: Path,
    out_path: Path,
    inplace: bool = False,
    limit: Optional[int] = None,
    sleep_sec: float = 0.35,
) -> Path:
    df = pd.read_parquet(catalog_in)

    # עמודות שנוסיף (לא דורס אם קיימות; רק ממלא NaN)
    add_cols = {
        "safety_overall": None,
        "safety_source_date": None,
        "recalls_count": None,
        "complaints_count": None,
        "has_market_price": None,
    }
    for c, default in add_cols.items():
        if c not in df.columns:
            df[c] = default

    # אינדיקציה למחיר Puppeteer שכבר יש לנו בדאטהבייס
    df["has_market_price"] = df.get("price_source", "").astype(str).map(_is_puppeteer_source)

    # רשימת יעדים לרענון:
    # נלך על יוניק לפי (year, make, model) כדי לא לפגוע בביצועים.
    keys = df[["year", "make", "model"]].dropna().drop_duplicates()
    if limit is not None:
        keys = keys.head(int(limit))

    safety_api = NhtsaSafety()
    recalls_api = NhtsaRecalls()

    total = len(keys)
    print(f"Planned to enrich {total} unique (year, make, model) combos.")

    # נעדכן לתוך DataFrame המקורי ב־mask לכל שילוב
    for i, row in keys.reset_index(drop=True).iterrows():
        y = int(row["year"])
        mk = str(row["make"])
        md = str(row["model"])

        try:
            safety, sdate, rc, cc = _nhtsa_safety_for((safety_api, recalls_api), y, mk, md)
        except Exception as e:
            print(f"[{i+1}/{total}] {y} {mk} {md} → API error: {e}")
            time.sleep(sleep_sec)
            continue

        mask = (df["year"] == y) & (df["make"] == mk) & (df["model"] == md)

        # לא נדרוס ערכים קיימים — נעדכן רק אם ריק/NaN
        if safety is not None:
            df.loc[mask & df["safety_overall"].isna(), "safety_overall"] = float(safety)
        if sdate:
            df.loc[mask & df["safety_source_date"].isna(), "safety_source_date"] = sdate
        if rc is not None:
            df.loc[mask & df["recalls_count"].isna(), "recalls_count"] = int(rc)
        if cc is not None:
            df.loc[mask & df["complaints_count"].isna(), "complaints_count"] = int(cc)

        if (i + 1) % 25 == 0 or (i + 1) == total:
            print(f"[{i+1}/{total}] enriched {y} {mk} {md} | safety={safety} recalls={rc} complaints={cc}")

        time.sleep(sleep_sec)

    # כתיבה
    out = catalog_in if inplace else out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"✅ wrote enriched catalog → {out}")
    return out

def parse_args():
    p = argparse.ArgumentParser(description="Enrich catalog with NHTSA safety/recalls/complaints + flags")
    p.add_argument("--in", dest="catalog_in", default="data/catalog_us.parquet", help="Input parquet")
    p.add_argument("--out", dest="catalog_out", default="data/catalog_us.enriched.parquet", help="Output parquet (ignored if --inplace)")
    p.add_argument("--inplace", action="store_true", help="Write back into input parquet")
    p.add_argument("--limit", type=int, default=None, help="Limit unique (year,make,model) to enrich (for testing)")
    p.add_argument("--sleep", type=float, default=0.35, help="Sleep seconds between API calls (be nice)")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    enrich_catalog(
        catalog_in=Path(args.catalog_in),
        out_path=Path(args.catalog_out),
        inplace=bool(args.inplace),
        limit=args.limit,
        sleep_sec=float(args.sleep),
    )