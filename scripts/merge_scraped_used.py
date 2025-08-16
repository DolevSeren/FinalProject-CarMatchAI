# scripts/merge_scraped_used.py
import argparse
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd


def _norm(s: str) -> str:
    # נורמליזציה זהה לזו שבסקריפטים אחרים כדי שמפתחות יתחברו
    return str(s).strip().replace("-", " ").replace("_", " ").title()


def load_catalog(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    # מפתחות נורמליים
    df["make_n"] = df["make"].map(_norm)
    df["model_n"] = df["model"].map(_norm)
    # ודא year שלם
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def _detect_scraped_schema(df: pd.DataFrame) -> Tuple[str, str, str]:
    """
    מזהה איזה סכימה יש לקובץ ה-scrape:
    - "clean": price_used_median / price_used_p25 / price_used_p75
    - "raw":   median / p25 / p75
    מחזיר שמות העמודות (median_col, p25_col, p75_col)
    """
    cols = {c.lower(): c for c in df.columns}

    # פורמט נקי
    if "price_used_median" in cols and "price_used_p25" in cols and "price_used_p75" in cols:
        return (cols["price_used_median"], cols["price_used_p25"], cols["price_used_p75"])

    # פורמט גולמי
    if "median" in cols:
        p25 = cols.get("p25") or cols.get("p_25") or cols.get("p25_price")
        p75 = cols.get("p75") or cols.get("p_75") or cols.get("p75_price")
        return (cols["median"], p25, p75)

    raise KeyError("Could not detect scraped schema (missing 'median' or 'price_used_median').")


def load_scraped(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    # לשמות הבסיסיים
    cols = {c.lower(): c for c in df.columns}

    # שדות חובה: year/make/model
    year_col = cols.get("year")
    make_col = cols.get("make")
    model_col = cols.get("model")
    if not all([year_col, make_col, model_col]):
        raise KeyError("scraped CSV must include year, make, model.")

    # זיהוי סכימת המחירים
    median_col, p25_col, p75_col = _detect_scraped_schema(df)

    # איחוד שמות לשפה אחת
    out = pd.DataFrame({
        "year": pd.to_numeric(df[year_col], errors="coerce").astype("Int64"),
        "make": df[make_col].astype(str),
        "model": df[model_col].astype(str),
        "price_used_median": pd.to_numeric(df[median_col], errors="coerce"),
    })
    if p25_col:
        out["price_used_p25"] = pd.to_numeric(df[p25_col], errors="coerce")
    if p75_col:
        out["price_used_p75"] = pd.to_numeric(df[p75_col], errors="coerce")

    # מקור + חותמת זמן אם קיימים
    source_col = cols.get("price_used_source_date") or cols.get("source") or cols.get("domain")
    scraped_at_col = cols.get("scraped_at") or cols.get("timestamp") or cols.get("scrapedat")
    if source_col in df.columns:
        out["src_domain"] = df[source_col].astype(str)
    else:
        out["src_domain"] = "www.cars.com"
    if scraped_at_col in df.columns:
        # נמשוך YYYY-MM-DD אם אפשר
        ts = pd.to_datetime(df[scraped_at_col], errors="coerce")
        out["src_date"] = ts.dt.strftime("%Y-%m-%d")
    else:
        out["src_date"] = datetime.utcnow().strftime("%Y-%m-%d")

    # נורמליזציה למפתח
    out["make_n"] = out["make"].map(_norm)
    out["model_n"] = out["model"].map(_norm)

    # סינון ערכים חסרים
    out = out.dropna(subset=["year", "make_n", "model_n", "price_used_median"])
    # טווחי מחיר סבירים בלבד
    out = out[(out["price_used_median"] >= 1000) & (out["price_used_median"] <= 300000)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--scraped", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cat = load_catalog(args.catalog)
    scr = load_scraped(args.scraped)

    # נשתמש ב-join על year/make_n/model_n
    key = ["year", "make_n", "model_n"]
    before_has_puppeteer = cat.get("price_used_source_date", pd.Series(dtype=object)).astype(str).str.startswith("puppeteer", na=False)
    before_cnt = int(before_has_puppeteer.sum()) if not before_has_puppeteer.empty else 0

    # נבנה מפה מרוכזת (במקרה שיש כפילויות)
    agg_cols = {
        "price_used_median": "median",
        "price_used_p25": "p25",
        "price_used_p75": "p75",
        "src_domain": "src_domain",
        "src_date": "src_date",
    }
    # נשמור את הרשומה האחרונה לכל מפתח (אפשר גם ממוצע/חציוני, כאן נעדיף אחרון)
    scr_sorted = scr.sort_values("src_date")
    scr_reduced = scr_sorted.groupby(key, as_index=False).last()

    merged = cat.merge(scr_reduced[key + ["price_used_median", "price_used_p25", "price_used_p75", "src_domain", "src_date"]],
                       how="left", on=key, suffixes=("", "_scr"))

    # עדכון רק אם יש median חדש
    has_new = merged["price_used_median_scr"].notna()

    for col_cat, col_scr in [("price_used_median", "price_used_median_scr"),
                             ("price_used_p25", "price_used_p25_scr"),
                             ("price_used_p75", "price_used_p75_scr")]:
        # צור עמודות אם לא קיימות
        if col_cat not in merged.columns:
            merged[col_cat] = np.nan
        merged.loc[has_new, col_cat] = merged.loc[has_new, col_scr]

    # price_used_source_date -> "puppeteer:{domain}@{date}"
    if "price_used_source_date" not in merged.columns:
        merged["price_used_source_date"] = None
    merged.loc[has_new, "price_used_source_date"] = (
        "puppeteer:" + merged.loc[has_new, "src_domain"].astype(str).str.strip()
        + "@" + merged.loc[has_new, "src_date"].astype(str).str.strip()
    )

    updated_rows = int(has_new.sum())
    after_has_puppeteer = merged["price_used_source_date"].astype(str).str.startswith("puppeteer", na=False)
    after_cnt = int(after_has_puppeteer.sum())

    # ניקוי עמודות עזר
    drop_cols = [c for c in merged.columns if c.endswith("_scr")] + ["src_domain", "src_date"]
    merged.drop(columns=drop_cols, inplace=True, errors="ignore")

    merged.to_parquet(args.out, index=False)
    print("✅ merged scraped used prices into catalog →", args.out)
    print(f"   updated rows: {updated_rows}")
    if before_cnt or after_cnt:
        print(f"   puppeteer rows before: {before_cnt} | after: {after_cnt}")


if __name__ == "__main__":
    main()
