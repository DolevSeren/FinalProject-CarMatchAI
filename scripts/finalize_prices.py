import argparse, pandas as pd, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_parquet(args.catalog)
    used = df.get("price_used_median")
    msrp = df.get("price_msrp_est")

    df["price_best"] = np.where(used.notna(), used, msrp)

    used_src = df.get("price_used_source_date")
    msrp_src_year = df.get("price_msrp_source_year")

    df["price_source"] = np.select(
        [
            used_src.notna(),
            used_src.isna() & msrp_src_year.notna()
        ],
        [
            used_src.astype(str),
            ("msrp_est@year=" + msrp_src_year.fillna("").astype(str)).str.replace("msrp_est@year=nan","", regex=False)
        ],
        default=None
    )

    # ניקוי חריגים
    mask_ok = df["price_best"].between(1000, 300000, inclusive="both")
    df.loc[~mask_ok, ["price_best","price_source"]] = [np.nan, None]

    df.to_parquet(args.out, index=False)
    print("✅ נוצר price_best + price_source. קובץ עודכן.")

if __name__ == "__main__":
    main()
