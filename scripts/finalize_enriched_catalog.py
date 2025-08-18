# scripts/finalize_enriched_catalog.py
from __future__ import annotations
import argparse, os, shutil
import pandas as pd
from datetime import datetime

def coerce_int(x, default=0):
    try:
        if pd.isna(x):
            return default
        return int(float(x))
    except Exception:
        return default

def coerce_bool(x):
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in ("1","true","yes","y","t"):
        return True
    if s in ("0","false","no","n","f","", "nan", "none", "null"):
        return False
    return False

def coerce_date_str(x):
    if x in (None, "", float("nan")) or pd.isna(x):
        return ""
    s = str(x).strip()
    # נשאיר כפי שהוא אם נראה כמו ISO; אחרת ננסה לפרסר
    try:
        # נסה parse
        dt = pd.to_datetime(s, errors="coerce", utc=True)
        if pd.isna(dt):
            return s
        # נחזיר תאריך בלבד (UTC) או timestamp קצר
        return dt.date().isoformat()
    except Exception:
        return s

def main():
    ap = argparse.ArgumentParser(description="Finalize/clean enriched catalog → overwrite main catalog_us.parquet safely.")
    ap.add_argument("--enriched", default="data/catalog_us.enriched.parquet", help="Path to enriched parquet")
    ap.add_argument("--out", default="data/catalog_us.parquet", help="Output path to overwrite (the main catalog)")
    ap.add_argument("--backup", default=None, help="Optional backup path. Default: <out>.backup.<YYYYmmdd-HHMMSS>.parquet")
    args = ap.parse_args()

    if not os.path.exists(args.enriched):
        raise SystemExit(f"Enriched file not found: {args.enriched}")

    print(f"Loading enriched catalog: {args.enriched}")
    df = pd.read_parquet(args.enriched)
    n0 = len(df)
    print(f"rows: {n0}")

    # ---- SAFETY MERGE ----
    # יש לנו שתי עמודות: overall_safety (ישן) ו-safety_overall (חדש וריק כרגע).
    # ניצור unified_overall_safety: ניקח קודם overall_safety; אם חסר, נמלא מ-safety_overall.
    if "overall_safety" not in df.columns:
        df["overall_safety"] = pd.NA
    if "safety_overall" not in df.columns:
        df["safety_overall"] = pd.NA

    unified = df["overall_safety"].copy()
    # אם יש ערכים ב-safety_overall (להבא), נשתמש בהם כדי למלא חסרים
    mask_need = unified.isna() & df["safety_overall"].notna()
    filled_from_new = int(mask_need.sum())
    unified[mask_need] = df.loc[mask_need, "safety_overall"]

    # נוודא שהטיפוס מספרי/float
    def _to_float_or_na(v):
        try:
            if pd.isna(v): return pd.NA
            return float(v)
        except Exception:
            return pd.NA
    unified = unified.map(_to_float_or_na)

    df["overall_safety"] = unified
    # נשאיר רק overall_safety, נסיר את safety_overall כדי למנוע בלבול
    if "safety_overall" in df.columns:
        df = df.drop(columns=["safety_overall"])

    print(f"Filled overall_safety from safety_overall for {filled_from_new} rows.")

    # ---- COUNTS / FLAGS CLEANUP ----
    for col in ["recalls_count", "complaints_count"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].map(coerce_int)

    if "has_market_price" not in df.columns:
        # נאתר לפי price_source שמתחיל ב-puppeteer
        src = df.get("price_source")
        if src is not None:
            df["has_market_price"] = src.astype(str).str.startswith("puppeteer")
        else:
            df["has_market_price"] = False
    df["has_market_price"] = df["has_market_price"].map(coerce_bool)

    if "safety_source_date" not in df.columns:
        df["safety_source_date"] = ""
    df["safety_source_date"] = df["safety_source_date"].map(coerce_date_str)

    # ---- ORDER COLUMNS (אופציונלי, נוח לקריאה) ----
    preferred_order = [
        "year","make","model","option_text","VClass","fuelType",
        "passengers","MPG_comb","Range_mi","electricRange_mi",
        "overall_safety","recalls_count","complaints_count","safety_source_date",
        "has_market_price","price_best","price_source","price_used_median","price_used_p25","price_used_p75",
        "price_msrp_est","price_msrp_source_year","price_used_source_date",
        "n_listings","vehicle_id","make_n","model_n","raw_fe_json",
    ]
    cols = [c for c in preferred_order if c in df.columns] + [c for c in df.columns if c not in preferred_order]
    df = df[cols]

    # ---- BACKUP & WRITE ----
    out = args.out
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup = args.backup or f"{out}.backup.{ts}.parquet"

    if os.path.exists(out):
        os.makedirs(os.path.dirname(backup) or ".", exist_ok=True)
        print(f"Backing up current catalog → {backup}")
        shutil.copy2(out, backup)

    print(f"Writing unified catalog → {out}")
    df.to_parquet(out, index=False)
    print("Done.")
    # תקציר קטן
    print("\nSummary:")
    print(" rows:", len(df))
    for col in ["overall_safety","recalls_count","complaints_count","has_market_price"]:
        nn = df[col].notna().sum()
        print(f" {col}: notnull={nn}")

if __name__ == "__main__":
    main()