# scripts/enrich_prices_used.py
import argparse, pandas as pd, numpy as np, sys, json
from pathlib import Path
from datetime import datetime

def _norm(s: str) -> str:
    return str(s).strip().replace("-", " ").replace("_", " ").title()

def load_cpi_series(path: Path):
    df = pd.read_csv(path)
    # Expect columns: date,value  (value = index)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].sort_index()

def cpi_ratio(cpi_series, snapshot_date: str, target_date: str) -> float:
    snap = cpi_series.asof(pd.to_datetime(snapshot_date))
    tgt  = cpi_series.asof(pd.to_datetime(target_date))
    if pd.isna(snap) or pd.isna(tgt) or snap == 0:
        return 1.0
    return float(tgt) / float(snap)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="data/catalog_us.parquet")
    ap.add_argument("--input", required=True, help="Used cars CSV (Kaggle)")
    ap.add_argument("--cpi-used", required=True, help="CPI series CSV for Used Cars (date,value)")
    ap.add_argument("--snapshot-date", default="2020-09-01", help="Approx snapshot date of the used dataset")
    ap.add_argument("--target-date", default=datetime.today().strftime("%Y-%m-%d"))
    ap.add_argument("--min_price", type=int, default=500)
    ap.add_argument("--max_price", type=int, default=250000)
    args = ap.parse_args()

    cat = pd.read_parquet(args.catalog)
    used = pd.read_csv(args.input, low_memory=False)

    # Try to infer price column
    price_col = next((c for c in used.columns if c.lower() in {"price","listing_price","usd_price"}), None)
    make_col  = next((c for c in used.columns if c.lower() in {"make","brand"}), None)
    model_col = next((c for c in used.columns if c.lower() in {"model"}), None)
    year_col  = next((c for c in used.columns if c.lower() in {"year","model_year"}), None)
    if not all([price_col, make_col, model_col, year_col]):
        sys.exit("❌ לא נמצאו עמודות year/make/model/price בקובץ ה‑Kaggle.")

    # Clean & normalize
    used = used[[year_col, make_col, model_col, price_col]].dropna()
    used = used.rename(columns={year_col:"year", make_col:"make", model_col:"model", price_col:"price"})
    used = used[(used["price"].astype(float) >= args.min_price) & (used["price"].astype(float) <= args.max_price)]
    used["year"] = pd.to_numeric(used["year"], errors="coerce").astype("Int64")
    used = used.dropna(subset=["year"])
    used["make_n"] = used["make"].map(_norm)
    used["model_n"] = used["model"].map(_norm)

    # Aggregate median / IQR
    agg = used.groupby(["year","make_n","model_n"])["price"].agg(
        price_used_median="median",
        price_used_p25=lambda s: s.quantile(0.25),
        price_used_p75=lambda s: s.quantile(0.75),
        n_listings="count"
    ).reset_index()

    # CPI adjust to target date
    cpi_used = load_cpi_series(Path(args.cpi_used))
    ratio = cpi_ratio(cpi_used, args.snapshot_date, args.target_date)
    for c in ["price_used_median","price_used_p25","price_used_p75"]:
        agg[c] = (agg[c] * ratio).round(0)

    # Prepare catalog side
    cat["make_n"] = cat["make"].map(_norm)
    cat["model_n"] = cat["model"].map(_norm)

    merged = cat.merge(agg, how="left", on=["year","make_n","model_n"])
    merged["price_used_source_date"] = np.where(
        merged["price_used_median"].notna(),
        f"used_snapshot@{args.snapshot_date}->adj@{args.target_date}",
        None
    )

    merged.drop(columns=["make_n","model_n"], inplace=True, errors="ignore")
    merged.to_parquet(args.catalog, index=False)
    print("✅ הוזרקו מחירי יד‑שנייה משוערים לקובץ הקטלוג.")

if __name__ == "__main__":
    main()
