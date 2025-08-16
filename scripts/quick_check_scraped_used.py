# scripts/quick_check_scraped_used.py
from __future__ import annotations
import os, sys, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPED = os.path.join(ROOT, "data", "scraped_used.csv")

def pct(n: int, d: int) -> str:
    return "0.0%" if not d else f"{(100.0 * n / d):.1f}%"

def num(n) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        try:
            return f"{float(n):,.0f}"
        except Exception:
            return str(n)

def print_df(df: pd.DataFrame, max_rows: int = 40) -> None:
    if df is None or df.empty:
        print("(empty)")
        return
    with pd.option_context("display.max_rows", max_rows, "display.max_columns", 120, "display.width", 220):
        print(df)

def main() -> int:
    if not os.path.exists(SCRAPED):
        print(f"❌ Missing {SCRAPED}")
        return 2

    df = pd.read_csv(SCRAPED)
    print(f"📄 scraped_used.csv rows (raw): {num(len(df))}")

    # שמירה על השורה האחרונה לכל key (במקרה של ניסיונות חוזרים)
    if "key" in df.columns and "price_used_source_date" in df.columns:
        df = df.sort_values("price_used_source_date").drop_duplicates(subset=["key"], keep="last")

    total = len(df)
    ok = (df["status"] == "ok").sum() if "status" in df.columns else 0
    no_price = (df["status"] == "no_price_timeout").sum() if "status" in df.columns else 0
    no_listings = (df["status"] == "no_listings").sum() if "status" in df.columns else 0
    errors = df["status"].str.startswith("error:").sum() if "status" in df.columns else 0

    print("\nStatus breakdown")
    print("================")
    print(f"Total unique keys:    {num(total)}")
    print(f"ok:                   {num(ok)}   ({pct(ok, total)})")
    print(f"no_price_timeout:     {num(no_price)}   ({pct(no_price, total)})")
    print(f"no_listings:          {num(no_listings)}   ({pct(no_listings, total)})")
    print(f"errors:               {num(errors)}   ({pct(errors, total)})")

    if "price_used_source_date" in df.columns:
        print("\nBy date (latest 15)")
        print("===================")
        date_counts = df["price_used_source_date"].value_counts().to_frame("rows").sort_index(ascending=False).head(15)
        print_df(date_counts)

    if "prices_count" in df.columns:
        print("\nPrices count distribution (ok rows)")
        print("===================================")
        ok_df = df[df["status"] == "ok"].copy()
        if not ok_df.empty:
            desc = ok_df["prices_count"].describe().to_frame(name="prices_count").T
            print_df(desc)
            print("\nTop 10 rows with most listings:")
            cols = [c for c in ["key","url","prices_count","price_used_median","price_used_p25","price_used_p75","price_used_source_date","status"] if c in ok_df.columns]
            print_df(ok_df.sort_values("prices_count", ascending=False).head(10)[cols])
        else:
            print("(no ok rows)")

    print("\n✅ Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
