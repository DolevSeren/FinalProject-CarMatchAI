import os
import sys
import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Load .env
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from matching.matcher import UserProfile
from agent.orchestrator import recommend_top_k

# LLM client — Ollama via OpenAI API format
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral")
llm = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

st.set_page_config(page_title="CarMatch AI – Chat", page_icon="🚗")
st.title("CarMatch AI — Your Car Buying Assistant")
st.caption("Powered locally by Mistral 7B via Ollama")

# ---------------- Questions ----------------
QUESTIONS = [
    ("new_or_used", "Do you prefer a new car, used, or either?"),
    ("usage", "What's your typical driving? city, highway, or mixed?"),
    ("typical_passengers", "How many people usually ride with you?"),
    ("annual_km", "How many kilometers do you drive per year?"),
    ("road_type", "Are your roads mostly flat, hilly, or mixed?"),
    ("budget_usd", "What's your budget in USD? (0 if flexible)"),
    ("current_car_likes", "What do you like in a car? (comma-separated)"),
    ("current_car_dislikes", "What do you dislike in a car? (comma-separated)"),
    ("special_needs", "Any special needs? (e.g., AWD, towing, high seating)")
]

# ------------- Smart number extraction -------------
def extract_number(text, default=0):
    """Use LLM to pull a numeric value from free text."""
    try:
        resp = llm.chat.completions.create(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": "Extract a single integer from the text. If unclear, estimate reasonably. Return only a number without commas/units."},
                {"role": "user", "content": text}
            ],
            temperature=0
        )
        return int(resp.choices[0].message.content.strip())
    except:
        return default

def extract_passenger_count(text): return extract_number(text, default=1)
def extract_km_count(text):        return extract_number(text, default=15000)
def extract_budget_usd(text):
    val = extract_number(text, default=0)
    return None if val == 0 else val

# ------------- Normalizers -------------
NORMALIZERS = {
    "new_or_used": lambda s: s.strip().lower(),
    "usage": lambda s: s.strip().lower(),
    "typical_passengers": extract_passenger_count,
    "annual_km": extract_km_count,
    "road_type": lambda s: s.strip().lower(),
    "budget_usd": extract_budget_usd,
    "current_car_likes": lambda s: [x.strip() for x in s.split(",") if x.strip()],
    "current_car_dislikes": lambda s: [x.strip() for x in s.split(",") if x.strip()],
    "special_needs": lambda s: [x.strip().lower() for x in s.split(",") if x.strip()],
}

# ------------- Session State -------------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! I’ll ask you 9 quick questions to find the best cars for you."}]
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "done" not in st.session_state:
    st.session_state.done = False
# pending confirmation/correction flow
if "pending" not in st.session_state:
    st.session_state.pending = None  # {"key":..., "stage":"confirm"|"correct", "original":..., "normalized":...}

# ------------- LLM helpers -------------
def llm_ack(prompt: str) -> str:
    """Short acknowledgement only (no self-intro)."""
    try:
        resp = llm.chat.completions.create(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": "Acknowledge the user's answer in a short, friendly sentence without introducing yourself or repeating the original question."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=50
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return ""

def llm_reflect(key: str, norm_value, original_text: str, current_answers: dict) -> str:
    """
    Generate a one-line reflection of what we inferred + ask for confirmation.
    Example: 'Got it — 5 passengers, so interior space matters. Did I get that right? (yes/no)'
    """
    try:
        context = {
            "key": key,
            "value": norm_value,
            "original": original_text,
            "answers_so_far": current_answers
        }
        resp = llm.chat.completions.create(
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system",
                 "content": (
                     "You are a car-buying copilot. Given the user's latest answer, write ONE short inference "
                     "that connects it to car needs (e.g., space, comfort, traction, efficiency, performance, budget). "
                     "Then end with: 'Did I get that right? (yes/no)' — keep total under 20 words."
                 )},
                {"role": "user", "content": json.dumps(context)}
            ],
            temperature=0.4,
            max_tokens=60
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback generic reflection
        pretty = f"{key.replace('_',' ')} = {norm_value}"
        return f"Got it — {pretty}. Did I get that right? (yes/no)"

def ask_next():
    i = st.session_state.q_index
    if i < len(QUESTIONS):
        _, question = QUESTIONS[i]
        st.session_state.messages.append({"role": "assistant", "content": question})
    else:
        st.session_state.done = True

# ------------- Render existing messages -------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Ask first question
if st.session_state.q_index == 0 and len(st.session_state.messages) == 1:
    ask_next()

# ------------- Chat input handling -------------
user_text = st.chat_input("Your answer...")
if user_text and not st.session_state.done:
    st.session_state.messages.append({"role": "user", "content": user_text})

    # If we're in a confirm/correct stage
    if st.session_state.pending:
        pend = st.session_state.pending
        key = pend["key"]
        stage = pend["stage"]

        if stage == "confirm":
            txt = user_text.strip().lower()
            if txt in ("y", "yes", "yeah", "correct", "right", "yep"):
                # confirmed → accept stored answer and move on
                st.session_state.messages.append({"role": "assistant", "content": "Great, noted."})
                st.session_state.pending = None
                st.session_state.q_index += 1
                if st.session_state.q_index < len(QUESTIONS):
                    ask_next()
                else:
                    st.session_state.done = True
                st.rerun()
            elif txt in ("n", "no", "nope", "wrong", "not quite"):
                # ask for correction
                _, question_text = QUESTIONS[st.session_state.q_index]
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"No problem — what's the correct answer for: \"{question_text}\"?"
                })
                st.session_state.pending["stage"] = "correct"
                st.rerun()
            else:
                # unclear confirmation → gently ask again
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Please reply yes or no. Did I get that right? (yes/no)"
                })
                st.rerun()

        elif stage == "correct":
            # Re-normalize with the corrected input
            try:
                norm = NORMALIZERS[key](user_text)
            except Exception:
                norm = user_text.strip()
            st.session_state.answers[key] = norm
            st.session_state.messages.append({"role": "assistant", "content": "Thanks, updated."})
            st.session_state.pending = None
            st.session_state.q_index += 1
            if st.session_state.q_index < len(QUESTIONS):
                ask_next()
            else:
                st.session_state.done = True
            st.rerun()

    else:
        # Normal flow: store answer → reflect → ask for confirmation
        key, _ = QUESTIONS[st.session_state.q_index]
        try:
            norm = NORMALIZERS[key](user_text)
        except Exception:
            norm = user_text.strip()
        st.session_state.answers[key] = norm

        # Optional tiny ack (kept very short)
        ack = llm_ack(user_text)
        if ack:
            st.session_state.messages.append({"role": "assistant", "content": ack})

        # Reflect & confirm
        reflection = llm_reflect(key, norm, user_text, st.session_state.answers)
        st.session_state.messages.append({"role": "assistant", "content": reflection})
        st.session_state.pending = {"key": key, "stage": "confirm", "original": user_text, "normalized": norm}
        st.rerun()

# ------------- After all questions → recommend -------------
if st.session_state.done and st.session_state.answers and not st.session_state.pending:
    a = st.session_state.answers
    profile = UserProfile(
        new_or_used=a.get("new_or_used", "either"),
        usage=a.get("usage", "mixed"),
        typical_passengers=int(a.get("typical_passengers", 4)),
        annual_km=int(a.get("annual_km", 15000)),
        road_type=a.get("road_type", "mixed"),
        budget_usd=a.get("budget_usd"),
        current_car_likes=a.get("current_car_likes", []),
        current_car_dislikes=a.get("current_car_dislikes", []),
        ownership_years=6,
        special_needs=a.get("special_needs", [])
    )

    with st.spinner("Finding matches..."):
        recs = recommend_top_k(profile, k=3)

    st.subheader("Top recommendations")
    for r in recs:
        title = f"{r['year']} {r['make']} {r['model']} ({r['body']})"
        # short reason using LLM
        try:
            reason_resp = llm.chat.completions.create(
                model=MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": "Explain in 1–2 concise sentences why this car fits the user's needs."},
                    {"role": "user", "content": json.dumps({"user_profile": a, "car": {"make": r["make"], "model": r["model"], "year": r["year"], "body": r["body"]}})}
                ],
                temperature=0.4,
                max_tokens=80
            )
            reason = reason_resp.choices[0].message.content.strip()
        except Exception:
            reason = "Balanced match for your usage and passengers with solid safety/comfort."

        with st.chat_message("assistant"):
            st.markdown(f"**{title}** — Score: {r.get('_score',0):.2f}")
            st.write(reason)

    # Save session log
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/session_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"answers": a, "top": [{k:v for k,v in r.items() if k in ['make','model','year','body','_score']} for r in recs]}) + "\n")
    except Exception:
        pass
