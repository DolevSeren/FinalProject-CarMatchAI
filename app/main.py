# app/main.py
# UI is English-only; הערות בעברית מותרות בתוך הקוד

from __future__ import annotations
import sys, os, pathlib
import streamlit as st

# ---------- Imports & path tweaks ----------
THIS = pathlib.Path(__file__).resolve()
ROOT = THIS.parent
PARENT = ROOT.parent
for extra in [ROOT, PARENT, pathlib.Path.cwd()]:
    p = str(extra)
    if p not in sys.path:
        sys.path.append(p)

try:
    from agent.orchestrator import get_recommendations
    from agent.llm import chat_acknowledge, chat_clarify_no, chat_summary_funny
except Exception:
    # Fallbacks if the project isn't structured as a package yet
    from orchestrator import get_recommendations  # type: ignore
    try:
        from llm import chat_acknowledge, chat_clarify_no, chat_summary_funny  # type: ignore
    except Exception:
        # No LLM helpers available — define safe fallbacks
        def chat_acknowledge(key, user_msg, answers):
            return {"text": f"Recorded {key}: {user_msg}", "require_confirm": False}
        def chat_clarify_no(field, answers):
            return "Got it — please correct me with the right value."
        def chat_summary_funny(answers):
            return "Quick recap: I'll fetch you great matches."

# ---------- Catalog path detection ----------
def detect_catalog_path() -> str | None:
    candidates = [
        os.getenv("CARMATCH_US_CATALOG"),
        "data/catalog_us.parquet",
        str(ROOT / "data" / "catalog_us.parquet"),
        str(PARENT / "data" / "catalog_us.parquet"),
        "catalog_us.parquet",
        str(ROOT / "catalog_us.parquet"),
        str(PARENT / "catalog_us.parquet"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

CATALOG_PATH = detect_catalog_path()
if CATALOG_PATH:
    os.environ["CARMATCH_US_CATALOG"] = CATALOG_PATH

# ---------------- App config ----------------
st.set_page_config(page_title="CarMatch AI – Global", layout="wide")
st.title("CarMatch AI – Global")
mode = st.radio("Mode", ["Chat", "Form"], index=0, horizontal=True)

# ---------------- Helpers -------------------
def normalize_condition(s: str) -> str:
    s = (s or "").strip().lower()
    if s in ["new", "n"]:
        return "new"
    if s in ["used", "u", "preowned", "pre-owned", "second hand", "second-hand"]:
        return "used"
    return "any"

def normalize_fuel(s: str) -> str:
    s = (s or "").strip().lower()
    # תמיכה גם ב-hybrid/diesel
    valid = {"bev","phev","gas","any","hybrid","diesel"}
    return s if s in valid else "any"

def parse_int(s: str, default=None):
    try:
        return int(str(s).replace(",", "").strip())
    except Exception:
        return default

def clean_one_line(text: str) -> str:
    """ מנקה שורות ורווחים, מחזיר טקסט שורה אחת """
    text = (text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines)

def as_score(x):
    try:
        return f"{float(x):.3f}"
    except Exception:
        return str(x)

# כל השאלות בסדר
QUESTIONS = [
    ("condition", "New or used? (new / used / any)"),
    ("budget_usd", "What's your budget in USD? (number)"),
    ("fuel_type", "Preferred fuel? (bev / phev / hybrid / diesel / gas / any)"),
    ("passengers", "How many passengers usually ride with you? (number)"),
    ("annual_km", "How many kilometers per year? (press Enter to skip)"),
    ("terrain", "Typical terrain? (flat / hilly, or leave blank)"),
    ("prioritize_mpg", "Prioritize efficiency (yes/no)?"),
    ("prioritize_safety", "Prioritize safety (yes/no)?"),
    ("prioritize_space", "Prioritize seating/space (yes/no)?"),
]

# --------------- CHAT MODE -------------------
if mode == "Chat":
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "I’ll ask a few quick questions to learn your needs, then recommend cars. Ready?"}
        ]
        st.session_state.step = 0
        st.session_state.answers = {}
        st.session_state.awaiting_answer = False
        st.session_state.awaiting_yes_no = False
        st.session_state.awaiting_clarification = False
        st.session_state.last_field = None
        st.session_state.results_shown = False
        # שאלה ראשונה
        key, question = QUESTIONS[st.session_state.step]
        st.session_state.chat_messages.append({"role": "assistant", "content": question})
        st.session_state.awaiting_answer = True

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    user_msg = st.chat_input("Your answer…")

    if user_msg:
        st.session_state.chat_messages.append({"role": "user", "content": user_msg})

        if st.session_state.awaiting_yes_no:
            ans = user_msg.strip().lower()
            if ans in ["yes", "y"]:
                st.session_state.awaiting_yes_no = False
                st.session_state.awaiting_answer = False
                st.session_state.awaiting_clarification = False
                st.session_state.step += 1
                if st.session_state.step < len(QUESTIONS):
                    key, question = QUESTIONS[st.session_state.step]
                    st.session_state.chat_messages.append({"role": "assistant", "content": question})
                    st.session_state.awaiting_answer = True
                st.rerun()
            elif ans in ["no", "n"]:
                clarify = chat_clarify_no(st.session_state.last_field, st.session_state.answers)
                st.session_state.chat_messages.append({"role": "assistant", "content": clean_one_line(clarify)})
                st.session_state.awaiting_yes_no = False
                st.session_state.awaiting_clarification = True
                st.rerun()
            else:
                st.session_state.chat_messages.append({"role": "assistant", "content": "Please answer with yes or no."})
                st.rerun()

        elif st.session_state.awaiting_clarification:
            key = st.session_state.last_field
            st.session_state.answers[f"{key}_clarification"] = user_msg.strip()
            st.session_state.awaiting_clarification = False
            st.session_state.step += 1
            if st.session_state.step < len(QUESTIONS):
                key, question = QUESTIONS[st.session_state.step]
                st.session_state.chat_messages.append({"role": "assistant", "content": question})
                st.session_state.awaiting_answer = True
            st.rerun()

        elif st.session_state.awaiting_answer and st.session_state.step < len(QUESTIONS):
            key, _ = QUESTIONS[st.session_state.step]
            st.session_state.last_field = key

            if key == "condition":
                st.session_state.answers["condition"] = normalize_condition(user_msg)
            elif key == "budget_usd":
                st.session_state.answers["budget_usd"] = parse_int(user_msg, None)
            elif key == "fuel_type":
                st.session_state.answers["fuel_type"] = normalize_fuel(user_msg)
            elif key == "passengers":
                st.session_state.answers["passengers"] = parse_int(user_msg, 1)
            elif key == "annual_km":
                st.session_state.answers["annual_km"] = parse_int(user_msg) if user_msg.strip() else None
            elif key == "terrain":
                t = user_msg.strip().lower()
                st.session_state.answers["terrain"] = t if t in ["flat", "hilly"] else "flat"
            elif key == "prioritize_mpg":
                st.session_state.answers["prioritize_mpg"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "prioritize_safety":
                st.session_state.answers["prioritize_safety"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "prioritize_space":
                st.session_state.answers["prioritize_space"] = user_msg.strip().lower() in ["yes", "y", "true"]

            ack_obj = chat_acknowledge(key, user_msg, st.session_state.answers)
            text = clean_one_line(ack_obj.get("text", ""))

            if ack_obj.get("require_confirm"):
                confirm_line = ack_obj.get("confirm_text") or "Did I get that right? (yes/no)"
                if not confirm_line.strip().lower().endswith("(yes/no)"):
                    confirm_line = confirm_line.rstrip(".?") + " (yes/no)"
                final_ack = f"{text} {confirm_line}".strip()
                st.session_state.chat_messages.append({"role": "assistant", "content": final_ack})
                st.session_state.awaiting_yes_no = True
                st.session_state.awaiting_answer = False
            else:
                st.session_state.chat_messages.append({"role": "assistant", "content": text})
                st.session_state.awaiting_answer = False
                st.session_state.step += 1
                if st.session_state.step < len(QUESTIONS):
                    key, question = QUESTIONS[st.session_state.step]
                    st.session_state.chat_messages.append({"role": "assistant", "content": question})
                    st.session_state.awaiting_answer = True
            st.rerun()

    # show results when done
    if (
        not st.session_state.awaiting_answer
        and not st.session_state.awaiting_yes_no
        and not st.session_state.awaiting_clarification
        and st.session_state.step >= len(QUESTIONS)
        and not st.session_state.results_shown
    ):
        with st.chat_message("assistant"):
            summary = chat_summary_funny(st.session_state.answers)
            st.write(clean_one_line(summary))
            st.write("Alright, let me crunch the numbers and find your match… 🚗💨")

        # Call orchestrator (returns unified list under "results")
        result = get_recommendations(st.session_state.answers, catalog_path=CATALOG_PATH)
        items = result.get("results", [])
        count = result.get("count", 0)

        with st.chat_message("assistant"):
            if not items:
                st.info("No vehicles matched your filters. Try relaxing constraints.")
            else:
                st.success(f"Found {count} vehicles. Showing top {min(10, len(items))}.")
                for i, it in enumerate(items[:10], start=1):
                    score = as_score(it.get("score"))
                    price = it.get("price_best")  # already formatted string if exists
                    src   = it.get("price_source") or "—"
                    price_txt = f" | {price} • {src}" if price else ""
                    st.markdown(f"**{i}. {it.get('make')} {it.get('model')}** — score {score}{price_txt}")
                    with st.expander("Why this pick?"):
                        reasons = it.get("reasons") or []
                        if isinstance(reasons, (list, tuple)):
                            for r in reasons:
                                st.markdown(f"- {r}")
                        else:
                            st.write(reasons)

        st.session_state.results_shown = True

    if st.button("Start a new chat"):
        st.session_state.clear()
        st.rerun()

# --------------- FORM MODE ---------------
else:
    with st.form("user_form"):
        condition = st.selectbox("New / Used / Any?", ["new", "used", "any"], index=2)
        budget = st.number_input("Budget (USD)", min_value=0, step=500, value=25000)
        fuel_type = st.selectbox("Fuel type", ["bev", "phev", "hybrid", "diesel", "gas", "any"], index=5)
        passengers = st.number_input("Passengers", min_value=1, max_value=9, value=4)
        annual_km = st.number_input("Annual kilometers", min_value=0, max_value=100000, value=12000, step=500)
        terrain = st.selectbox("Terrain", ["flat", "hilly"], index=0)
        st.subheader("Priorities")
        prioritize_mpg = st.checkbox("Efficiency (MPG/Range)", value=True)
        prioritize_safety = st.checkbox("Safety", value=True)
        prioritize_space = st.checkbox("Seating/space", value=False)
        submitted = st.form_submit_button("Get recommendations")

    if submitted:
        answers = dict(
            condition=condition,
            budget_usd=budget if budget > 0 else None,
            fuel_type=fuel_type,
            passengers=int(passengers),
            annual_km=int(annual_km),
            terrain=terrain,
            prioritize_mpg=bool(prioritize_mpg),
            prioritize_safety=bool(prioritize_safety),
            prioritize_space=bool(prioritize_space),
            top_n=10,
        )
        result = get_recommendations(answers, catalog_path=CATALOG_PATH)
        items = result.get("results", [])
        if not items:
            st.info("No vehicles matched your filters. Try relaxing constraints.")
        else:
            import pandas as pd
            cols = [c for c in [
                "make","model","option_text","VClass","fuelType",
                "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
                "price_best","price_source","annual_fuel_cost","score"
            ] if items and c in items[0]]
            df = pd.DataFrame([{k: it.get(k) for k in cols} for it in items])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.subheader("Why these picks?")
            for i, it in enumerate(items[:10], start=1):
                with st.expander(f"#{i} — {it.get('make')} {it.get('model')} (score {as_score(it.get('score'))})"):
                    reasons = it.get("reasons") or []
                    if isinstance(reasons, (list, tuple)):
                        for r in reasons:
                            st.markdown(f"- {r}")
                    else:
                        st.write(reasons)
