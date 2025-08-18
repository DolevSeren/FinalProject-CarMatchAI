# app/streamlit_app.py
# UI is English-only; Hebrew comments allowed in code.

import os, sys, io
import pathlib
import datetime as dt
import streamlit as st

# ---------- Import orchestration ----------
THIS = pathlib.Path(__file__).resolve()
ROOT = THIS.parent
for extra in [ROOT, ROOT.parent, pathlib.Path.cwd()]:
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

try:
    from agent.orchestrator import get_recommendations
except Exception:
    from orchestrator import get_recommendations  # type: ignore

# ---------- Catalog path detection ----------
def detect_catalog_path() -> str | None:
    candidates = [
        os.getenv("CARMATCH_US_CATALOG"),
        "data/catalog_us.parquet",
        str(ROOT / "data" / "catalog_us.parquet"),
        str(ROOT.parent / "data" / "catalog_us.parquet"),
        "catalog_us.parquet",
        str(ROOT / "catalog_us.parquet"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

CATALOG_PATH = detect_catalog_path()
if CATALOG_PATH:
    os.environ["CARMATCH_US_CATALOG"] = CATALOG_PATH

TOP_SHOW = 3

# ---------- Helpers ----------
def _to_float_or_none(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None

def _freshness_from_source(src: str | None) -> str | None:
    if not src:
        return None
    s = str(src)
    if not s.startswith("puppeteer"):
        return None
    if "@" not in s:
        return None
    try:
        return s.split("@")[-1]
    except Exception:
        return None

def _filter_puppeteer_only(items):
    return [it for it in items if str(it.get("price_source","")).startswith("puppeteer")]

def _items_to_dataframe(items):
    import pandas as pd
    def row_map(it):
        d = dict(it)
        d["price_freshness"] = _freshness_from_source(d.get("price_source"))
        return d
    rows = [row_map(it) for it in items]
    cols = [c for c in [
        "make","model","option_text","VClass","fuelType",
        "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
        "price_best","price_source","price_freshness","annual_fuel_cost","score"
    ] if rows and c in rows[0]]
    import pandas as pd
    return pd.DataFrame([{k: r.get(k) for k in cols} for r in rows])

def _advice_banner(answers: dict):
    msgs = []
    if (answers.get("annual_km") or 0) < 10000:
        msgs.append("You drive <10k km/year — fuel economy has **low impact** on annual costs, so I won’t emphasize it.")
    if not answers.get("prioritize_safety", True):
        msgs.append("You deprioritized safety — I won’t weigh safety scores.")
    if (answers.get("ownership_years") or 0) >= 5:
        msgs.append("Planning to keep >4 years — I’ll **emphasize reliability** (recalls/complaints).")
    if msgs:
        st.info("  \n".join(msgs))

# ---------- App UI ----------
st.set_page_config(page_title="CarMatch AI – Global", layout="wide")
st.title("CarMatch AI – Global")

with st.sidebar:
    st.header("User Preferences")
    condition = st.selectbox("Condition", ["any", "new", "used"], index=0)
    usage = st.radio("Usage pattern", ["mixed", "city", "highway"], index=0, horizontal=True)
    passengers = st.number_input("Passengers", min_value=1, max_value=9, value=4, step=1)
    annual_km = st.number_input("Annual kilometers", min_value=0, max_value=100000, value=12000, step=500)
    terrain = st.selectbox("Typical terrain", ["flat", "hilly"], index=0)
    ownership_years = st.number_input("Planned ownership (years)", min_value=1, max_value=15, value=3)
    budget_str = st.text_input("Budget (USD, optional)", value="25000")
    fuel_type = st.selectbox("Fuel type filter", ["any", "gas", "hybrid", "phev", "bev", "diesel"], index=0)

    st.divider()
    st.subheader("Constraints & diversity")
    min_mpg_str = st.text_input("Min combined MPG (optional)", value="")
    max_per_model = st.slider("Max vehicles per model", 1, 3, 1)
    max_share_per_fuel = st.slider("Max share per single fuel-type", 0.5, 1.0, 0.7, step=0.05)

    st.divider()
    st.subheader("Data Quality")
    puppeteer_only = st.checkbox("Show only vehicles with real market price (Puppeteer)", value=False)

col_left, col_right = st.columns([1,1])
with col_left:
    run = st.button("Find cars", type="primary")
with col_right:
    st.write("Catalog:", CATALOG_PATH if CATALOG_PATH else "Not found (set CARMATCH_US_CATALOG)")

if run:
    answers = {
        "condition": condition,
        "usage": usage,
        "passengers": int(passengers),
        "annual_km": int(annual_km),
        "terrain": terrain,
        "ownership_years": int(ownership_years),
        "budget_usd": _to_float_or_none(budget_str),
        "fuel_type": fuel_type,
        "top_n": TOP_SHOW,  # תמיד 3
        "min_mpg": _to_float_or_none(min_mpg_str),
        "max_per_model": int(max_per_model),
        "max_share_per_fuel": float(max_share_per_fuel),
        "prioritize_mpg": True,
        "prioritize_safety": True,
        "prioritize_space": False,
    }

    _advice_banner(answers)

    with st.spinner("Ranking cars..."):
        try:
            result = get_recommendations(answers, catalog_path=CATALOG_PATH)
        except Exception as e:
            st.error(f"Failed to get recommendations: {e}")
            st.stop()

    items = (result.get("results", []) or [])[:TOP_SHOW]
    if puppeteer_only:
        items = _filter_puppeteer_only(items)

    # enrich display text with freshness
    for it in items:
        src = str(it.get("price_source","")) or ""
        fresh = _freshness_from_source(src)
        if fresh and it.get("price_best"):
            it["price_best"] = f"{it['price_best']} (as of {fresh})"

    st.success(f"Found {len(items)} vehicles")
    if not items:
        st.info("No vehicles matched your filters. Try relaxing constraints.")
    else:
        df = _items_to_dataframe(items)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download CSV
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_bytes = csv_buf.getvalue().encode("utf-8")
        st.download_button(
            "Download results as CSV",
            data=csv_bytes,
            file_name=f"carmatch_results_{dt.date.today().isoformat()}.csv",
            mime="text/csv",
        )

        # Reasons per row
        st.subheader("Why these picks?")
        for i, it in enumerate(items, start=1):
            reasons = it.get("reasons") or []
            with st.expander(f"#{i} — {it.get('make')} {it.get('model')} (score {it.get('score')})"):
                if isinstance(reasons, (list, tuple)):
                    for r in reasons:
                        st.markdown(f"- {r}")
                else:
                    st.write(reasons)