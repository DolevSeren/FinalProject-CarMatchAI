
# app/streamlit_app.py (drop-in)
# UI is English-only; Hebrew comments allowed in code.

import os, sys
import pathlib
import streamlit as st

# ---------- Import orchestration ----------
# Allow running either from project root or from this file's folder
THIS = pathlib.Path(__file__).resolve()
ROOT = THIS.parent
for extra in [ROOT, ROOT.parent, pathlib.Path.cwd()]:
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

try:
    from agent.orchestrator import get_recommendations
except Exception:
    # Fallback: if the project isn't packaged as agent/* yet, try local orchestrator.py
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
    budget_str = st.text_input("Budget (USD, optional)", value="25000")
    fuel_type = st.selectbox("Fuel type filter", ["any", "gas", "phev", "bev"], index=0)

    st.divider()
    st.subheader("Ranking Options")
    top_n = st.slider("Top N", min_value=3, max_value=50, value=10, step=1)
    min_mpg_str = st.text_input("Min combined MPG (optional)", value="")
    max_per_model = st.slider("Max vehicles per model", 1, 3, 1)
    max_share_per_fuel = st.slider("Max share per single fuel-type", 0.5, 1.0, 0.7, step=0.05)

    st.divider()
    st.subheader("Priorities")
    prioritize_mpg = st.checkbox("Prioritize efficiency (MPG/Range)", value=True)
    prioritize_safety = st.checkbox("Prioritize safety", value=True)
    prioritize_space = st.checkbox("Prioritize seating/space", value=False)

    st.caption("Tip: You can paste weights override as JSON under the 'Advanced' section.")
    with st.expander("Advanced (weights override JSON)"):
        weights_json = st.text_area("weights (JSON)", value="", height=120,
                                    placeholder='e.g. {"mpg":0.5, "safety":0.3, "passengers":0.2}')

col_left, col_right = st.columns([1,1])

with col_left:
    run = st.button("Find cars", type="primary")

with col_right:
    st.write("Catalog:", CATALOG_PATH if CATALOG_PATH else "Not found (set CARMATCH_US_CATALOG)")

def _to_float_or_none(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None

if run:
    answers = {
        "condition": condition,
        "usage": usage,
        "passengers": int(passengers),
        "annual_km": int(annual_km),
        "terrain": terrain,
        "budget_usd": _to_float_or_none(budget_str),
        "fuel_type": fuel_type,
        "top_n": int(top_n),
        "min_mpg": _to_float_or_none(min_mpg_str),
        "max_per_model": int(max_per_model),
        "max_share_per_fuel": float(max_share_per_fuel),
        "prioritize_mpg": bool(prioritize_mpg),
        "prioritize_safety": bool(prioritize_safety),
        "prioritize_space": bool(prioritize_space),
    }

    # Optional weights override
    weights = {}
    if weights_json.strip():
        try:
            import json
            weights = json.loads(weights_json)
            if isinstance(weights, dict):
                answers["weights"] = weights
        except Exception as e:
            st.warning(f"Invalid weights JSON: {e}")

    # Set env for catalog if our detection found one
    catalog_path = CATALOG_PATH
    if catalog_path:
        os.environ["CARMATCH_US_CATALOG"] = catalog_path

    with st.spinner("Ranking cars..."):
        try:
            result = get_recommendations(answers, catalog_path=catalog_path)
        except Exception as e:
            st.error(f"Failed to get recommendations: {e}")
            st.stop()

    st.success(f"Found {result.get('count', 0)} vehicles")
    # Show profile used
    with st.expander("Profile used for ranking"):
        st.json(result.get("profile", {}))

    items = result.get("results", [])
    if not items:
        st.info("No vehicles matched your filters. Try relaxing constraints.")
    else:
        # Simple grid view
        import pandas as pd
        cols = [c for c in [
            "make","model","option_text","VClass","fuelType",
            "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
            "price_best","price_source","annual_fuel_cost","score"
        ] if items and c in items[0]]
        df = pd.DataFrame([{k: it.get(k) for k in cols} for it in items])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Reasons per row
        st.subheader("Why these picks?")
        for i, it in enumerate(items, start=1):
            with st.expander(f"#{i} — {it.get('make')} {it.get('model')} (score {it.get('score')})"):
                reasons = it.get("reasons") or []
                if isinstance(reasons, (list, tuple)):
                    for r in reasons:
                        st.markdown(f"- {r}")
                else:
                    st.write(reasons)
