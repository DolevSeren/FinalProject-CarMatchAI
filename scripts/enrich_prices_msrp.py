# scripts/enrich_prices_msrp.py
import argparse, pandas as pd, numpy as np, sys
from pathlib import Path
from datetime import datetime

def _norm(s: str) -> str:
    return str(s).strip().replace("-", " ").replace("_", " ").title()

def load_cpi_series(path: Path):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].sort_index()

def cpi_ratio(cpi_series, source_year: int, target_date: str) -> float:
    src = cpi_series.asof(pd.to_datetime(f"{source_year}-12-31"))
    tgt = cpi_series.asof(pd.to_datetime(target_date))
    if pd.isna(src) or pd.isna(tgt) or src == 0:
        return 1.0
    return float(tgt) / float(src)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="data/catalog_us.parquet")
    ap.add_argument("--input", required=True, help="New cars MSRP CSV (make,model,year,msrp)")
    ap.add_argument("--cpi-new", required=True, help="CPI series CSV for New Vehicles (date,value)")
    ap.add_argument("--source-year", type=int, default=2023)
    ap.add_argument("--target-date", default=datetime.today().strftime("%Y-%m-%d"))
    ap.add_argument("--min_msrp", type=int, default=10000)
    ap.add_argument("--max_msrp", type=int, default=300000)
    args = ap.parse_args()

    cat = pd.read_parquet(args.catalog)
    msrp = pd.read_csv(args.input)

    # Columns detection
    msrp_cols = {c.lower(): c for c in msrp.columns}
    for needed in ("make","model","year"):
        if needed not in msrp_cols:
            sys.exit("❌ קובץ MSRP חייב לכלול make, model, year, msrp.")
    price_col = None
    for k in ("msrp","price","usd_msrp"):
        if k in msrp_cols:
            price_col = msrp_cols[k]
            break
    if not price_col:
        sys.exit("❌ לא נמצאה עמודת MSRP בקובץ.")

    msrp = msrp.rename(columns={
        msrp_cols["make"]: "make",
        msrp_cols["model"]: "model",
        msrp_cols["year"]: "year",
        price_col: "msrp"
    })
    msrp["make_n"] = msrp["make"].map(_norm)
    msrp["model_n"] = msrp["model"].map(_norm)
    msrp["year"]   = pd.to_numeric(msrp["year"], errors="coerce").astype("Int64")
    msrp = msrp.dropna(subset=["year","msrp"])
    msrp = msrp[(msrp["msrp"] >= args.min_msrp) & (msrp["msrp"] <= args.max_msrp)]

    # CPI adjust
    cpi = load_cpi_series(Path(args.cpi_new))
    ratio = cpi_ratio(cpi, args.source_year, args.target_date)
    msrp["price_msrp_est"] = (msrp["msrp"] * ratio).round(0)

    # Prepare catalog
    cat["make_n"]  = cat["make"].map(_norm)
    cat["model_n"] = cat["model"].map(_norm)

    merged = cat.merge(
        msrp[["year","make_n","model_n","price_msrp_est"]],
        how="left", on=["year","make_n","model_n"]
    )

    # רק אם אין מחיר יד‑שנייה—נשתמש ב‑MSRP
    use_msrp_mask = merged["price_msrp_est"].notna() & merged["price_used_median"].isna()
    merged.loc[use_msrp_mask, "price_msrp_source_year"] = args.source_year

    merged.drop(columns=["make_n","model_n"], inplace=True, errors="ignore")
    merged.to_parquet(args.catalog, index=False)
    print("✅ הוזרקו מחירי MSRP מוערכים (CPI‑adjusted) היכן שלא היו מחירי יד‑שנייה.")

if __name__ == "__main__":
    main()
