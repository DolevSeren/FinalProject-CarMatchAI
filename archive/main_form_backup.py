# app/main.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from matching.matcher import UserProfile
from agent.orchestrator import recommend_top_k

from dotenv import load_dotenv
load_dotenv()

print("DEBUG:", os.getenv("OPENAI_BASE_URL"))

st.set_page_config(page_title="CarMatch AI (MVP)", page_icon="🚗")

st.title("CarMatch AI – MVP (English, live-on-demand)")
st.caption("No database. Cars only. Mock now → live web later.")

with st.form("profile"):
    col1, col2 = st.columns(2)
    with col1:
        new_or_used = st.selectbox("New or used?", ["either","new","used"])
        usage = st.selectbox("Usage", ["mixed","city","highway"])
        passengers = st.number_input("Typical passengers", 1, 7, 4)
        annual_km = st.number_input("Annual km", 1000, 50000, 15000, step=1000)
        road_type = st.selectbox("Road type", ["mixed","flat","hilly"])
    with col2:
        budget = st.number_input("Budget (USD, 0 = no limit)", 0, 200000, 32000, step=1000)
        likes = st.text_input("What do you like in a car?", "handling, quiet")
        dislikes = st.text_input("What do you dislike?", "stiff ride")
        years = st.number_input("Planned ownership (years)", 1, 12, 6)
        needs = st.text_input("Special needs (comma-separated)", "awd, high_seating")
    submitted = st.form_submit_button("Get my top 3")

if submitted:
    profile = UserProfile(
        new_or_used=new_or_used,
        usage=usage,
        typical_passengers=int(passengers),
        annual_km=int(annual_km),
        road_type=road_type,
        budget_usd=int(budget) if budget>0 else None,
        current_car_likes=[s.strip() for s in likes.split(",") if s.strip()],
        current_car_dislikes=[s.strip() for s in dislikes.split(",") if s.strip()],
        ownership_years=int(years),
        special_needs=[s.strip() for s in needs.split(",") if s.strip()]
    )
    with st.spinner("Thinking..."):
        recs = recommend_top_k(profile, k=3)
    st.subheader("Recommended cars for you")
    if not recs:
        st.info("No matches. Try raising budget or lowering constraints.")
    for r in recs:
        title = f"{r['year']} {r['make']} {r['model']} ({r['body']})"
        st.markdown(f"### {title} — Score: **{r.get('_score',0):.3f}**")
        cols = st.columns(3)
        cols[0].metric("MSRP (new)", f"${r['msrp_usd']:,}" if r.get("msrp_usd") else "Unknown")
        cols[1].metric("Used median", f"${r['used_median']:,}" if r.get("used_median") else "Unknown")
        cols[2].write(", ".join(r.get("equipment", [])[:3]) or "—")
        with st.expander("Why this car?"):
            st.write("Highlights:", r["why"]["highlights"])
            st.write("Trade‑offs:", r["why"]["tradeoffs"])
            st.write("Sources:", r["why"]["sources"])
