# scripts/quick_check_prices.py
from __future__ import annotations
import os
import sys
import pathlib
import re
from typing import Optional

import pandas as pd


# ---------------- Path & catalog detection ----------------
THIS = pathlib.Path(__file__).resolve()
ROOT = THIS.parent.parent  # project root (…/FinalProject-CarMatchAI)
CANDIDATES = [
    os.getenv("CARMATCH_US_CATALOG"),
    str(ROOT / "data" / "catalog_us.parquet"),
    "data/catalog_us.parquet",
    str(ROOT / "catalog_us.parquet"),
    "catalog_us.parquet",
]

def detect_catalog_path() -> Optional[str]:
    for p in CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


# ---------------- Pretty helpers ----------------
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


def h1(s: str) -> None:
    print("\n" + s)
    print("=" * len(s))


def h2(s: str) -> None:
    print("\n" + s)
    print("-" * len(s))


def print_df(df: pd.DataFrame, max_rows: int = 30) -> None:
    if df.empty:
        print("(empty)")
        return
    with pd.option_context("display.max_rows", max_rows, "display.max_columns", 40, "display.width", 200):
        print(df)


# ---------------- Main logic ----------------
def analyze(catalog_path: Optional[str] = None) -> int:
    path = catalog_path or detect_catalog_path()
    if not path:
        print("❌ Could not find catalog_us.parquet. Set CARMATCH_US_CATALOG or place it under data/")
        return 2

    print(f"📦 Catalog: {path}")
    df = pd.read_parquet(path)

    total = len(df)
    has_price = df["price_best"].notna() if "price_best" in df.columns else pd.Series([False] * total)
    n_price = int(has_price.sum())

    # Sources
    src_col = df["price_source"].astype(str) if "price_source" in df.columns else pd.Series([""] * total)
    is_pupp = src_col.str.startswith("puppeteer", na=False)
    is_msrp = src_col.str.contains("msrp", case=False, na=False)

    n_pupp = int(is_pupp.sum())
    n_msrp = int(is_msrp.sum())

    # Basic summary
    h1("Price Coverage Summary")
    print(f"Total rows:            {num(total)}")
    print(f"With price_best:       {num(n_price)}  ({pct(n_price, total)})")
    print(f" • From puppeteer:     {num(n_pupp)}  ({pct(n_pupp, total)})")
    print(f" • From MSRP (est):    {num(n_msrp)}  ({pct(n_msrp, total)})")

    # Coverage by fuel type
    h2("Coverage by fuelType")
    if "fuelType" in df.columns:
        by_fuel = (
            df.assign(_has_price=has_price)
              .groupby("fuelType", dropna=False)["_has_price"]
              .agg(["count", "sum"])
              .rename(columns={"count": "rows", "sum": "with_price"})
        )
        by_fuel["coverage"] = (100.0 * by_fuel["with_price"] / by_fuel["rows"]).round(1).astype(str) + "%"
        by_fuel = by_fuel.sort_values("rows", ascending=False)
        print_df(by_fuel)
    else:
        print("(fuelType column missing)")

    # Coverage by year
    h2("Coverage by year")
    if "year" in df.columns:
        by_year = (
            df.assign(_has_price=has_price)
              .groupby("year", dropna=False)["_has_price"]
              .agg(["count", "sum"])
              .rename(columns={"count": "rows", "sum": "with_price"})
              .sort_index(ascending=False)
        )
        by_year["coverage"] = (100.0 * by_year["with_price"] / by_year["rows"]).round(1).astype(str) + "%"
        print_df(by_year)
    else:
        print("(year column missing)")

    # Top makes coverage
    h2("Top makes by rows (with coverage)")
    if "make" in df.columns:
        by_make = (
            df.assign(_has_price=has_price)
              .groupby("make", dropna=False)["_has_price"]
              .agg(["count", "sum"])
              .rename(columns={"count": "rows", "sum": "with_price"})
        )
        by_make["coverage"] = (100.0 * by_make["with_price"] / by_make["rows"]).round(1)
        by_make = by_make.sort_values("rows", ascending=False)
        print_df(by_make.head(25).assign(coverage=lambda x: x["coverage"].astype(str) + "%"))
    else:
        print("(make column missing)")

    # Sanity peek: a few rows that have price, with source
    h2("Sample rows with price (head 10)")
    cols = [c for c in ["make","model","year","price_best","price_source","fuelType","VClass"] if c in df.columns]
    print_df(df.loc[has_price, cols].head(10))

    # Sanity peek: rows without price
    h2("Sample rows without price (head 10)")
    print_df(df.loc[~has_price, cols].head(10))

    # Optional: puppeteer recency breakdown (by date suffix in source)
    h2("Puppeteer source dates (recency)")
    if n_pupp > 0:
        dates = (
            src_col[is_pupp]
            .str.extract(r"@(\d{4}-\d{2}-\d{2})")[0]
            .value_counts(dropna=False)
            .rename_axis("date")
            .to_frame("rows")
            .sort_index(ascending=False)
        )
        print_df(dates.head(20))
    else:
        print("(no puppeteer sources)")

    print("\n✅ Done.")
    return 0


if __name__ == "__main__":
    # Allow passing an explicit path: python scripts/quick_check_prices.py /path/to/catalog.parquet
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(analyze(path_arg))
