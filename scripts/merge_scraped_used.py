import argparse, pandas as pd, numpy as np

def _norm(s: str) -> str:
    return str(s).strip().replace("-", " ").replace("_", " ").title()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="data/catalog_us.parquet")
    ap.add_argument("--scraped", default="data/scraped_used.csv")
    ap.add_argument("--out", default="data/catalog_us.parquet")
    args = ap.parse_args()

    cat = pd.read_parquet(args.catalog)
    scr = pd.read_csv(args.scraped)

    # בדיקות מינימום
    need_cols = {"year","make","model","price_used_median","price_used_p25","price_used_p75"}
    missing = need_cols - set(c.lower() for c in scr.columns)
    # נתאים שמות עמודות לאותיות קטנות
    cols_map = {c.lower(): c for c in scr.columns}
    if missing:
        raise SystemExit(f"❌ scraped csv missing columns: {missing}")

    # נרמול שמות
    scr = scr.rename(columns={cols_map["year"]:"year", cols_map["make"]:"make", cols_map["model"]:"model",
                              cols_map["price_used_median"]:"price_used_median",
                              cols_map["price_used_p25"]:"price_used_p25",
                              cols_map["price_used_p75"]:"price_used_p75"})
    if "n_listings" in cols_map:
        scr = scr.rename(columns={cols_map["n_listings"]:"n_listings"})
    if "source" in cols_map:
        scr = scr.rename(columns={cols_map["source"]:"source"})
    if "scraped_at" in cols_map:
        scr = scr.rename(columns={cols_map["scraped_at"]:"scraped_at"})

    scr["year"] = pd.to_numeric(scr["year"], errors="coerce").astype("Int64")
    scr = scr.dropna(subset=["year","make","model"])
    scr["make_n"] = scr["make"].map(_norm)
    scr["model_n"] = scr["model"].map(_norm)

    cat["make_n"]  = cat["make"].map(_norm)
    cat["model_n"] = cat["model"].map(_norm)

    merged = cat.merge(
        scr[["year","make_n","model_n","price_used_median","price_used_p25","price_used_p75","n_listings","source","scraped_at"]],
        how="left", on=["year","make_n","model_n"], suffixes=("", "_scr")
    )

    mask = merged["price_used_median_scr"].notna()

    # עדכון מחירי used לפי scraped
    for col in ["price_used_median","price_used_p25","price_used_p75"]:
        src_col = f"{col}_scr"
        if src_col in merged.columns:
            merged.loc[mask, col] = merged.loc[mask, src_col]

    # מקור + תאריך
    src = merged.get("source", pd.Series(index=merged.index, dtype="string")).astype("string").fillna("puppeteer")
    at  = pd.to_datetime(merged.get("scraped_at"), errors="coerce").dt.date.astype("string")
    src_tag = (src + "@" + at).str.replace("@<NA>", "", regex=False)

    if "price_used_source_date" not in merged.columns:
        merged["price_used_source_date"] = pd.NA
    merged.loc[mask, "price_used_source_date"] = src_tag.loc[mask]

    # ניקוי עמודות עזר
    merged.drop(columns=[c for c in merged.columns if c.endswith("_scr")] + ["make_n","model_n"], inplace=True, errors="ignore")

    merged.to_parquet(args.out, index=False)
    print(f"✅ merged scraped used prices into catalog → {args.out}")
    print(f"   updated rows: {int(mask.sum())}")

if __name__ == "__main__":
    main()
