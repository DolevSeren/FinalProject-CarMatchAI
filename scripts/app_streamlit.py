import streamlit as st
import pandas as pd
from matching.engine import load_catalog, UserProfile, rank_cars

st.set_page_config(page_title="CarMatch AI — MVP Matcher", layout="wide")

st.title("CarMatch AI — Matching Engine (MVP)")

with st.sidebar:
    st.header("Profile")
    usage = st.selectbox("Usage", ["mixed", "city", "highway"], index=0)
    passengers = st.number_input("Passengers", min_value=1, max_value=9, value=4, step=1)
    annual_km = st.number_input("Annual km", min_value=0, max_value=200_000, value=12000, step=1000)
    terrain = st.selectbox("Terrain", ["flat", "hilly"], index=0)
    budget = st.number_input("Budget (USD) — optional", min_value=0, max_value=500_000, value=0, step=1000)
    budget = None if budget == 0 else float(budget)

    st.header("Filters & Diversity")
    top_n = st.slider("Top N", min_value=5, max_value=50, value=15, step=1)
    min_mpg = st.slider("Min MPG/MPGe", min_value=0, max_value=120, value=0, step=1)
    max_per_model = st.slider("Max per model", min_value=1, max_value=3, value=1, step=1)
    max_share_per_fuel = st.slider("Max share per fuel type", min_value=0.3, max_value=1.0, value=0.7, step=0.05)

    st.header("Catalog")
    catalog_path = st.text_input("Catalog path", value="data/catalog_us.parquet")

    if st.button("Run matching", use_container_width=True):
        st.session_state["run"] = True
        st.session_state["args"] = dict(
            usage=usage, passengers=passengers, annual_km=annual_km, terrain=terrain,
            budget=budget, top_n=top_n, min_mpg=min_mpg if min_mpg > 0 else None,
            max_per_model=max_per_model, max_share_per_fuel=float(max_share_per_fuel),
            catalog_path=catalog_path,
        )

if st.session_state.get("run"):
    args = st.session_state["args"]
    try:
        catalog = load_catalog(args["catalog_path"])
    except Exception as e:
        st.error(f"Failed to load catalog: {e}")
        st.stop()

    profile = UserProfile(
        usage=args["usage"],
        passengers=int(args["passengers"]),
        annual_km=int(args["annual_km"]),
        terrain=args["terrain"],
        budget=args["budget"],
    )

    df = rank_cars(
        profile,
        catalog,
        top_n=int(args["top_n"]),
        min_mpg=args["min_mpg"],
        max_per_model=int(args["max_per_model"]),
        max_share_per_fuel=float(args["max_share_per_fuel"]),
    )

    if df.empty:
        st.warning("No vehicles matched your filters. Try relaxing constraints.")
    else:
        st.success(f"Found {len(df)} matches")
        show_cols = [c for c in ["make","model","option_text","VClass","fuelType","passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi","score"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True)

        st.subheader("Reasons")
        for i, reasons in enumerate(df.get("reasons", []), start=1):
            with st.expander(f"#{i} — reasons"):
                for r in reasons:
                    st.write("•", r)
