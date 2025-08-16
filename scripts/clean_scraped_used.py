# scripts/clean_scraped_used.py
import argparse, os, pandas as pd, numpy as np
from datetime import datetime

ALT_COLS = {
    "median": ("price_used_median", "median", "price_median"),
    "p25":    ("price_used_p25", "p25", "q25"),
    "p75":    ("price_used_p75", "p75", "q75"),
    "n":      ("n_listings", "n", "count"),
    "source": ("price_used_source_date", "source"),
}

def pick(df, candidates, default=None):
    for c in candidates:
        if c in df.columns:
            return c
    return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/scraped_used.csv", help="input scraped csv")
    ap.add_argument("--out", default="data/scraped_used.clean.csv", help="output cleaned csv")
    ap.add_argument("--min_n", type=int, default=10, help="minimal listings per (year,make,model)")
    ap.add_argument("--min_price", type=int, default=1000)
    ap.add_argument("--max_price", type=int, default=300000)
    args = ap.parse_args()

    if not os.path.exists(args.inp):
        raise SystemExit(f"❌ input not found: {args.inp}")

    df = pd.read_csv(args.inp)
    # normalize required columns
    for col in ["year","make","model"]:
        if col not in df.columns:
            raise SystemExit(f"❌ missing column '{col}' in {args.inp}")

    c_med = pick(df, ALT_COLS["median"])
    if not c_med:
        raise SystemExit("❌ missing median price column (expected one of: price_used_median/median/price_median)")

    c_p25 = pick(df, ALT_COLS["p25"])
    c_p75 = pick(df, ALT_COLS["p75"])
    c_n   = pick(df, ALT_COLS["n"])
    c_src = pick(df, ALT_COLS["source"])

    out = df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")

    # rename if needed
    rename_map = {}
    if c_med != "price_used_median": rename_map[c_med] = "price_used_median"
    if c_p25 and c_p25 != "price_used_p25": rename_map[c_p25] = "price_used_p25"
    if c_p75 and c_p75 != "price_used_p75": rename_map[c_p75] = "price_used_p75"
    if c_n   and c_n   != "n_listings":     rename_map[c_n]   = "n_listings"
    if c_src and c_src != "price_used_source_date": rename_map[c_src] = "price_used_source_date"
    if rename_map:
        out = out.rename(columns=rename_map)

    # coerce numeric
    for c in ["price_used_median","price_used_p25","price_used_p75","n_listings"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    # fill p25/p75 if missing (±10% סביב החציון – עדיף משהו מאשר כלום)
    if "price_used_p25" not in out.columns or out["price_used_p25"].isna().all():
        out["price_used_p25"] = (out["price_used_median"] * 0.9).round(0)
    if "price_used_p75" not in out.columns or out["price_used_p75"].isna().all():
        out["price_used_p75"] = (out["price_used_median"] * 1.1).round(0)

    # sanity bounds
    ok = out["price_used_median"].between(args.min_price, args.max_price, inclusive="both")
    before = len(out)
    out = out[ok].copy()

    # minimal sample size
    if "n_listings" in out.columns:
        out = out[out["n_listings"].fillna(0) >= args.min_n].copy()

    # de-dup by (year,make,model) – שמור את השורה העדכנית ביותר לפי מקור/זמן אם קיים
    # נפיל קודם חותמת זמן "ככל הנראה" מתוך מקור אם קיים, אחרת עכשיו
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if "price_used_source_date" in out.columns:
        # השאר כמחרוזת; נשתמש בה רק לשמירה אינפורמטיבית
        pass
    else:
        out["price_used_source_date"] = f"puppeteer:unknown@{ts}"

    out = (out
           .sort_values(["year","make","model","price_used_source_date"])
           .drop_duplicates(subset=["year","make","model"], keep="last")
           .reset_index(drop=True))

    # final report
    after = len(out)
    print(f"cleaned rows: {after} (from {before})")
    print("sample:\n", out.head(8).to_string(index=False))

    out.to_csv(args.out, index=False)
    print(f"✅ wrote cleaned file → {args.out}")

if __name__ == "__main__":
    main()
