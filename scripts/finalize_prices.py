# scripts/finalize_prices.py
import argparse, pandas as pd, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="data/catalog_us.parquet")
    ap.add_argument("--out", default="data/catalog_us.parquet")
    args = ap.parse_args()

    df = pd.read_parquet(args.catalog)

    # ודא שהעמודות קיימות (גם אם ריקות)
    for c in ["price_used_median", "price_used_source_date", "price_msrp_est", "price_msrp_source_year"]:
        if c not in df.columns:
            df[c] = np.nan

    used = df["price_used_median"]
    msrp = df["price_msrp_est"]

    # price_best: עדיפות ליד-שנייה, אחרת MSRP
    df["price_best"] = np.where(used.notna(), used, msrp)

    # price_source: וקטורית, בלי or על Series
    used_src = df["price_used_source_date"].astype("string")
    used_src = used_src.fillna("used_snapshot")  # ברירת מחדל אם אין תאריך מקור
    msrp_src_year = df["price_msrp_source_year"].astype("Int64").astype("string")
    msrp_src = "msrp_est@year=" + msrp_src_year.fillna("")

    df["price_source"] = np.select(
        [
            used.notna(),                    # יש מחיר יד-שנייה
            used.isna() & msrp.notna(),     # אין יד-שנייה, יש MSRP
        ],
        [
            used_src,
            msrp_src.str.strip()
        ],
        default=None
    )

    # ננקה ערכים לא הגיוניים אם נשארו
    mask_ok = df["price_best"].between(1000, 300000, inclusive="both")
    df.loc[~mask_ok, ["price_best", "price_source"]] = [np.nan, None]

    df.to_parquet(args.out, index=False)
    print("✅ נוצר price_best + price_source. קובץ עודכן.")

if __name__ == "__main__":
    main()
