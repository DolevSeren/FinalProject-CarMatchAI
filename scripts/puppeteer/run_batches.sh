#!/usr/bin/env bash
set -euo pipefail

# go to scripts/puppeteer
cd "$(dirname "$0")"

ROOT="$(cd ../.. && pwd)"
TARGETS_CSV="$ROOT/data/targets.csv"
OUT_SCRAPED="$ROOT/data/scraped_used.csv"

# -------- sanity checks --------
if [[ ! -f "$TARGETS_CSV" ]]; then
  echo "❌ Missing $TARGETS_CSV"
  exit 1
fi

TOTAL_LINES=$(wc -l < "$TARGETS_CSV")
if [[ -z "${TOTAL_LINES:-}" || "$TOTAL_LINES" -lt 2 ]]; then
  echo "❌ $TARGETS_CSV has no data (lines=$TOTAL_LINES)"
  exit 1
fi

# subtract header
TARGETS=$(( TOTAL_LINES - 1 ))
echo "Targets (without header): $TARGETS"

# -------- runtime knobs --------
export RATE_LIMIT_MS=${RATE_LIMIT_MS:-4000}
export PRICE_TIMEOUT_MS=${PRICE_TIMEOUT_MS:-10000}
export NAV_TIMEOUT_MS=${NAV_TIMEOUT_MS:-15000}
export PAGELOAD_TIMEOUT_MS=${PAGELOAD_TIMEOUT_MS:-15000}
export MAX_LISTINGS_PER_PAGE=${MAX_LISTINGS_PER_PAGE:-60}

# -------- run in 20-sized batches --------
OFFSET_START=${1:-0}   # optional arg: start offset
BATCH_SIZE=${BATCH_SIZE:-20}

for (( OFFSET=OFFSET_START; OFFSET < TARGETS; OFFSET+=BATCH_SIZE )); do
  echo ">>> OFFSET=$OFFSET / TARGETS=$TARGETS"
  OFFSET=$OFFSET LIMIT=$BATCH_SIZE node scrape_used.js || true
done

# -------- merge + finalize + quick check --------
cd "$ROOT"
python scripts/merge_scraped_used.py   --catalog data/catalog_us.parquet --scraped "$OUT_SCRAPED" --out data/catalog_us.parquet
python scripts/finalize_prices.py      --catalog data/catalog_us.parquet --out   data/catalog_us.parquet
python scripts/quick_check_prices.py
