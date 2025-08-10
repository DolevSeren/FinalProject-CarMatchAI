# app/main.py
# UI is English-only; הערות בעברית מותרות בתוך הקוד

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agent.orchestrator import get_recommendations
from agent.llm import chat_acknowledge, chat_clarify_no, chat_summary_funny

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
    valid = ["bev", "phev", "gas", "any"]
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

# כל השאלות בסדר
QUESTIONS = [
    ("condition", "New or used? (new / used / any)"),
    ("budget_usd", "What's your budget in USD? (number)"),
    ("fuel_type", "Preferred fuel? (bev / phev / gas / any)"),
    ("passengers", "How many passengers usually ride with you? (number)"),
    ("annual_km", "How many kilometers per year? (press Enter to skip)"),
    ("terrain", "Typical terrain? (flat / hilly, or leave blank)"),
    ("comfort_priority", "Is comfort a priority? (yes/no)"),
    ("fun_priority", "Is fun-to-drive more important than efficiency? (yes/no)"),
    ("years_to_keep", "How many years do you plan to keep the car? (number)"),
    ("special_needs", "Any special needs? comma-separated (tow_hook, awd, high_seating) or leave blank"),
]

def ask_next_question():
    key, question = QUESTIONS[st.session_state.step]
    st.session_state.chat_messages.append({"role": "assistant", "content": question})
    st.session_state.awaiting_answer = True

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
        ask_next_question()

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    user_msg = st.chat_input("Your answer...")

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
                    ask_next_question()
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
                ask_next_question()
            st.rerun()

        elif st.session_state.awaiting_answer and st.session_state.step < len(QUESTIONS):
            key, _ = QUESTIONS[st.session_state.step]
            st.session_state.last_field = key

            if key == "condition":
                st.session_state.answers["condition"] = normalize_condition(user_msg)
            elif key == "budget_usd":
                st.session_state.answers["budget_usd"] = parse_int(user_msg, 0)
            elif key == "fuel_type":
                st.session_state.answers["fuel_type"] = normalize_fuel(user_msg)
            elif key == "passengers":
                st.session_state.answers["passengers"] = parse_int(user_msg, 1)
            elif key == "annual_km":
                st.session_state.answers["annual_km"] = parse_int(user_msg) if user_msg.strip() else None
            elif key == "terrain":
                t = user_msg.strip().lower()
                st.session_state.answers["terrain"] = t if t in ["flat", "hilly"] else None
            elif key == "comfort_priority":
                st.session_state.answers["comfort_priority"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "fun_priority":
                st.session_state.answers["fun_priority"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "years_to_keep":
                st.session_state.answers["years_to_keep"] = parse_int(user_msg, 5)
            elif key == "special_needs":
                needs = [x.strip() for x in user_msg.split(",") if x.strip()] if user_msg.strip() else []
                st.session_state.answers["special_needs"] = needs

            ack_obj = chat_acknowledge(key, user_msg, st.session_state.answers)
            text = clean_one_line(ack_obj.get("text", ""))

            if ack_obj.get("skip"):
                st.session_state.awaiting_answer = False
                st.session_state.step += 1
                if st.session_state.step < len(QUESTIONS):
                    ask_next_question()
                st.rerun()

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
                    ask_next_question()
            st.rerun()

    if (not st.session_state.awaiting_answer
        and not st.session_state.awaiting_yes_no
        and not st.session_state.awaiting_clarification
        and st.session_state.step >= len(QUESTIONS)
        and not st.session_state.results_shown):

        with st.chat_message("assistant"):
            summary = chat_summary_funny(st.session_state.answers)
            st.write(clean_one_line(summary))
            st.write("Alright, let me crunch the numbers and find your match… 🚗💨")

        user, result = get_recommendations(st.session_state.answers, api_key="")

        if "new" in result and "used" in result:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("New")
                for car, score in result["new"]:
                    st.write(f"**{car.make} {car.model}** — score {score} | est. ${car.price_new_usd:,.0f}")
            with col2:
                st.subheader("Used")
                for car, score in result["used"]:
                    st.write(f"**{car.make} {car.model}** — score {score} | est. ${car.price_used_usd:,.0f}")
        else:
            key = "new" if "new" in result else "used"
            st.subheader(key.capitalize())
            for car, score in result[key]:
                price = car.price_new_usd if key == "new" else car.price_used_usd
                st.write(f"**{car.make} {car.model}** — score {score} | est. ${price:,.0f}")

        st.session_state.results_shown = True

    if st.button("Start a new chat"):
        st.session_state.clear()
        st.rerun()

# --------------- FORM MODE ---------------
else:
    with st.form("user_form"):
        condition = st.selectbox("New / Used / Any?", ["new", "used", "any"], index=2)
        budget = st.number_input("Budget (USD)", min_value=5000, step=500, value=30000)
        fuel_type = st.selectbox("Fuel type", ["bev", "phev", "gas", "any"], index=3)
        passengers = st.number_input("Passengers", min_value=1, max_value=8, value=4)
        comfort = st.checkbox("Comfort is a priority")
        fun = st.checkbox("Fun-to-drive is a priority")
        terrain = st.selectbox("Terrain", ["", "flat", "hilly"], index=0)
        years = st.number_input("Years to keep", min_value=1, max_value=12, value=5)
        needs = st.multiselect("Special needs", ["tow_hook", "awd", "high_seating"])
        submitted = st.form_submit_button("Get recommendations")

    if submitted:
        answers = dict(
            condition=condition, budget_usd=budget, fuel_type=fuel_type,
            passengers=passengers, comfort_priority=comfort, fun_priority=fun,
            terrain=terrain or None, years_to_keep=years, special_needs=needs
        )
        user, result = get_recommendations(answers, api_key="")
        if "new" in result and "used" in result:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("New")
                for car, score in result["new"]:
                    st.write(f"**{car.make} {car.model}** — score {score} | est. ${car.price_new_usd:,.0f}")
            with col2:
                st.subheader("Used")
                for car, score in result["used"]:
                    st.write(f"**{car.make} {car.model}** — score {score} | est. ${car.price_used_usd:,.0f}")
        else:
            key = "new" if "new" in result else "used"
            st.subheader(key.capitalize())
            for car, score in result[key]:
                price = car.price_new_usd if key == "new" else car.price_used_usd
                st.write(f"**{car.make} {car.model}** — score {score} | est. ${price:,.0f}")
