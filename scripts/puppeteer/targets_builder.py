# scripts/puppeteer/targets_builder.py
from __future__ import annotations
import os
import sys
import csv
import hashlib
import pathlib
from urllib.parse import quote_plus

"""
Builds data/targets.csv with URL per row from a seed CSV that has year,make,model columns.
If the input already has a 'url' column, it passes rows through (normalizing key if needed).

Usage:
  python scripts/puppeteer/targets_builder.py \
      --input data/targets.csv \
      --out data/targets.csv

Notes:
- By default, --input=data/targets.csv and --out=data/targets.csv (in-place upgrade).
- You can set search ZIP (for Cars.com) via env SEARCH_ZIP (default 10001).
- URL format uses the 'q=' free text search to avoid make/model slug issues.
"""

DEFAULT_INPUT = "data/targets.csv"
DEFAULT_OUT = "data/targets.csv"
DEFAULT_ZIP = os.getenv("SEARCH_ZIP", "10001")

def sha1_short(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]

def build_url(year: str, make: str, model: str, zip_code: str) -> str:
    query = f"{year} {make} {model}".strip()
    q = quote_plus(query)
    # We search nationwide (maximum_distance=all) on used listings, anchored to a ZIP (cars.com requires a ZIP in the URL)
    return (
        "https://www.cars.com/shopping/results/"
        f"?q={q}"
        "&stock_type=used"
        "&maximum_distance=all"
        f"&zip={zip_code}"
    )

def normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "").replace("_", "")

def detect_cols(header: list[str]) -> dict:
    norm = [normalize_header(h) for h in header]
    idx = { "year": None, "make": None, "model": None, "url": None, "key": None }
    for i, h in enumerate(norm):
        if h == "year" and idx["year"] is None:
            idx["year"] = i
        elif h == "make" and idx["make"] is None:
            idx["make"] = i
        elif h == "model" and idx["model"] is None:
            idx["model"] = i
        elif h == "url" and idx["url"] is None:
            idx["url"] = i
        elif h == "key" and idx["key"] is None:
            idx["key"] = i
    return idx

def main(args: list[str]) -> int:
    # parse args
    in_path = DEFAULT_INPUT
    out_path = DEFAULT_OUT
    for i, a in enumerate(args):
        if a == "--input" and i + 1 < len(args):
            in_path = args[i + 1]
        if a == "--out" and i + 1 < len(args):
            out_path = args[i + 1]

    root = pathlib.Path(__file__).resolve().parents[2]  # project root
    in_abs = (root / in_path).resolve() if not os.path.isabs(in_path) else pathlib.Path(in_path)
    out_abs = (root / out_path).resolve() if not os.path.isabs(out_path) else pathlib.Path(out_path)

    if not in_abs.exists():
        print(f"❌ Input not found: {in_abs}")
        return 2

    zip_code = DEFAULT_ZIP
    print(f"📥 Input:  {in_abs}")
    print(f"📤 Output: {out_abs}")
    print(f"📍 ZIP:    {zip_code}")

    rows_out: list[dict] = []
    seen_keys = set()

    with in_abs.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("❌ Input CSV is empty")
            return 2

        idx = detect_cols(header)
        has_url = idx["url"] is not None

        # rebuild a dict reader using original header to preserve any extra columns
        f.seek(0)
        dict_reader = csv.DictReader(f)

        for row in dict_reader:
            # read fields safely irrespective of spacing/case
            year = row.get("year") or row.get("Year") or ""
            make = row.get("make") or row.get("Make") or ""
            model = row.get("model") or row.get("Model") or ""
            url = row.get("url") or row.get("URL") or ""

            year = str(year).strip()
            make = str(make).strip()
            model = str(model).strip()
            url = str(url).strip()

            if not has_url:
                if not (year and make and model):
                    continue  # skip incomplete rows
                url = build_url(year, make, model, zip_code)

            # key: prefer existing, else derive from URL (stable), else from year/make/model
            key = (row.get("key") or row.get("KEY") or "").strip()
            if not key:
                base = url if url else f"{year}|{make}|{model}"
                key = sha1_short(base, 10)

            # output row
            out = {
                "key": key,
                "url": url,
                "year": year,
                "make": make,
                "model": model,
            }
            # attach any extra columns if present
            for k, v in row.items():
                if k not in out and k is not None:
                    out[k] = v

            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows_out.append(out)

    if not rows_out:
        print("❌ No usable rows produced (check your input columns).")
        return 3

    # ensure parent folder exists
    out_abs.parent.mkdir(parents=True, exist_ok=True)

    # write output
    fieldnames = ["key", "url", "year", "make", "model"]
    # include any extra headers consistently
    extra_keys = set()
    for r in rows_out:
        extra_keys.update(k for k in r.keys() if k not in fieldnames)
    fieldnames.extend(sorted(extra_keys))

    with out_abs.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)

    print(f"✅ Wrote {len(rows_out)} targets to {out_abs}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
