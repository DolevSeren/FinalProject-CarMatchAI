import os, pandas as pd, numpy as np, random
from pathlib import Path

CAT_PATH = "data/catalog_us.parquet" if os.path.exists("data/catalog_us.parquet") else "catalog_us.parquet"
OUT = "data/targets.csv"

def pick_sample(df, n=300, seed=42):
    random.seed(seed)
    df = df.copy()
    # רק דגמים עם make/model/year
    df = df.dropna(subset=["make","model","year"])
    # קידום חשמלי/פופולריים
    bev_mask = df["fuelType"].astype(str).str.contains("Electric", case=False, na=False)
    hot = pd.concat([
        df[bev_mask].sample(min(100, bev_mask.sum()), random_state=seed) if bev_mask.any() else df.head(0),
        df.sample(min(n, len(df)), random_state=seed)
    ], ignore_index=True).drop_duplicates(subset=["year","make","model"])
    hot = hot.sample(min(n, len(hot)), random_state=seed)
    return hot[["year","make","model"]]

def main():
    if not os.path.exists(CAT_PATH):
        raise SystemExit(f"❌ Catalog not found at {CAT_PATH}")
    df = pd.read_parquet(CAT_PATH)
    sample = pick_sample(df, n=300)
    Path("data").mkdir(exist_ok=True)
    sample.to_csv(OUT, index=False)
    print(f"✔ wrote {OUT} with {len(sample)} rows")

if __name__ == "__main__":
    main()
