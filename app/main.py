# app/main.py
# UI is English-only; הערות בעברית מותרות בתוך הקוד

from __future__ import annotations
import sys, os, io, pathlib, datetime as dt
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
    from agent.llm import chat_acknowledge, chat_clarify_no, chat_summary_funny, chat_explain_pick
except Exception:
    from orchestrator import get_recommendations  # type: ignore
    try:
        from llm import chat_acknowledge, chat_clarify_no, chat_summary_funny, chat_explain_pick  # type: ignore
    except Exception:
        def chat_acknowledge(key, user_msg, answers):
            return {"text": f"Recorded {key}: {user_msg}", "require_confirm": False}
        def chat_clarify_no(field, answers):
            return "Got it — please correct me with the right value."
        def chat_summary_funny(answers):
            return "Quick recap: I'll fetch you great matches."
        def chat_explain_pick(item, answers):
            return f"{item.get('year','')} {item.get('make')} {item.get('model')} looks like a solid fit."

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

with st.sidebar:
    st.subheader("Data Quality")
    puppeteer_only = st.checkbox("Show only vehicles with real market price (Puppeteer)", value=False)

# ---------------- Helpers -------------------
NO_CONFIRM_KEYS = {"budget_usd", "fuel_type", "ownership_years", "prioritize_safety", "prioritize_space"}
# terrain יכול להיות ללא אישור כשהדלק כבר לא חשוב (כדי לא לחפור)
TERRAIN_NO_CONFIRM_IF_LOW_KM = True

def normalize_condition(s: str) -> str:
    s = (s or "").strip().lower()
    if s in ["new", "n"]:
        return "new"
    if s in ["used", "u", "preowned", "pre-owned", "second hand", "second-hand"]:
        return "used"
    return "any"

def normalize_fuel(s: str) -> str:
    s = (s or "").strip().lower()
    valid = {"bev","phev","gas","any","hybrid","diesel"}
    return s if s in valid else "any"

def parse_int(s: str, default=None):
    try:
        return int(str(s).replace(",", "").strip())
    except Exception:
        return default

def clean_one_line(text: str) -> str:
    text = (text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines)

def as_score(x):
    try:
        return f"{float(x):.3f}"
    except Exception:
        return str(x)

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

def _advice_banner(answers: dict):
    msgs = []
    if (answers.get("annual_km") or 0) < 10000:
        msgs.append("You drive under 10k km/year, so fuel economy likely won’t change your annual costs much. I’ll de-emphasize it.")
    if not answers.get("prioritize_safety", True):
        msgs.append("You chose not to prioritize safety. I’ll ignore safety scores in the ranking.")
    if (answers.get("ownership_years") or 0) >= 5:
        msgs.append("You plan to keep the car over 4 years. I’ll emphasize reliability (recalls/complaints).")
    if msgs:
        st.info("  \n".join(msgs))

def _simple_recap(a: dict) -> str:
    parts = []
    if a.get("condition") and a["condition"] != "any":
        parts.append(f"You’re open to {a['condition']} cars.")
    if a.get("budget_usd"):
        parts.append(f"Budget is about ${a['budget_usd']:,}.")
    if a.get("fuel_type") and a["fuel_type"] != "any":
        parts.append(f"Fuel preference: {a['fuel_type']}.")
    if a.get("passengers"):
        p = int(a["passengers"])
        if p <= 2:
            parts.append("You usually drive solo or with one passenger, so space isn’t critical.")
        elif p >= 5:
            parts.append("You often have 5+ passengers, so we’ll focus on roomier options.")
        else:
            parts.append(f"Typically {p} passengers.")
    km = a.get("annual_km")
    if km:
        if km < 10000:
            parts.append("You drive relatively little each year, so fuel economy matters less.")
        else:
            parts.append(f"You drive ~{km:,} km/year, so efficiency can save you money.")
    yrs = a.get("ownership_years")
    if yrs:
        if yrs >= 5:
            parts.append(f"You plan to keep the car ~{yrs} years, so reliability will be emphasized.")
        else:
            parts.append(f"Planned ownership is ~{yrs} years.")
    return " ".join(parts) or "Got it. I’ll tailor recommendations to your answers."

TOP_SHOW = 3  # מציגים תמיד עד 3 תוצאות

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
        st.session_state.advice_shown = False  # כדי לא להציג את הבאנר כפול
        key, question = [
            ("condition", "New or used? (new / used / any)"),
            ("budget_usd", "What's your budget in USD? (number)"),
            ("fuel_type", "Preferred fuel? (bev / phev / hybrid / diesel / gas / any)"),
            ("passengers", "How many passengers usually ride with you? (number)"),
            ("annual_km", "How many kilometers per year? (press Enter to skip)"),
            ("terrain", "Typical terrain? (flat / hilly, or leave blank)"),
            ("ownership_years", "How many years do you plan to keep the car? (number)"),
            ("prioritize_mpg", "Prioritize efficiency (yes/no)?"),
            ("prioritize_safety", "Prioritize safety (yes/no)?"),
            ("prioritize_space", "Prioritize seating/space (yes/no)?"),
        ][st.session_state.step]
        st.session_state.QUESTIONS = [
            ("condition", "New or used? (new / used / any)"),
            ("budget_usd", "What's your budget in USD? (number)"),
            ("fuel_type", "Preferred fuel? (bev / phev / hybrid / diesel / gas / any)"),
            ("passengers", "How many passengers usually ride with you? (number)"),
            ("annual_km", "How many kilometers per year? (press Enter to skip)"),
            ("terrain", "Typical terrain? (flat / hilly, or leave blank)"),
            ("ownership_years", "How many years do you plan to keep the car? (number)"),
            ("prioritize_mpg", "Prioritize efficiency (yes/no)?"),
            ("prioritize_safety", "Prioritize safety (yes/no)?"),
            ("prioritize_space", "Prioritize seating/space (yes/no)?"),
        ]
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
                # דילוג על prioritize_mpg אם כבר ענינו עליו
                while st.session_state.step < len(st.session_state.QUESTIONS):
                    next_key, question = st.session_state.QUESTIONS[st.session_state.step]
                    if next_key == "prioritize_mpg" and st.session_state.answers.get("prioritize_mpg") is not None:
                        st.session_state.step += 1
                        continue
                    st.session_state.chat_messages.append({"role": "assistant", "content": question})
                    st.session_state.awaiting_answer = True
                    break
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
            # דילוג על prioritize_mpg אם כבר ענינו עליו
            while st.session_state.step < len(st.session_state.QUESTIONS):
                next_key, question = st.session_state.QUESTIONS[st.session_state.step]
                if next_key == "prioritize_mpg" and st.session_state.answers.get("prioritize_mpg") is not None:
                    st.session_state.step += 1
                    continue
                st.session_state.chat_messages.append({"role": "assistant", "content": question})
                st.session_state.awaiting_answer = True
                break
            st.rerun()

        elif st.session_state.awaiting_answer and st.session_state.step < len(st.session_state.QUESTIONS):
            key, _ = st.session_state.QUESTIONS[st.session_state.step]
            st.session_state.last_field = key

            # Persist answer
            if key == "condition":
                st.session_state.answers["condition"] = normalize_condition(user_msg)
            elif key == "budget_usd":
                st.session_state.answers["budget_usd"] = parse_int(user_msg, None)
            elif key == "fuel_type":
                st.session_state.answers["fuel_type"] = normalize_fuel(user_msg)
            elif key == "passengers":
                st.session_state.answers["passengers"] = parse_int(user_msg, 1)
            elif key == "annual_km":
                km_val = parse_int(user_msg) if user_msg.strip() else None
                st.session_state.answers["annual_km"] = km_val
                # אם <10k — נכבה את MPG ונסמן לדלג על השאלה. לא מוסיפים הודעה ידנית (כדי למנוע כפילות)!
                if km_val is not None and km_val < 10000:
                    st.session_state.answers["prioritize_mpg"] = False
                    st.session_state.skip_mpg_question = True
            elif key == "terrain":
                t = user_msg.strip().lower()
                st.session_state.answers["terrain"] = t if t in ["flat", "hilly"] else "flat"
            elif key == "ownership_years":
                st.session_state.answers["ownership_years"] = parse_int(user_msg, 3)
            elif key == "prioritize_mpg":
                st.session_state.answers["prioritize_mpg"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "prioritize_safety":
                st.session_state.answers["prioritize_safety"] = user_msg.strip().lower() in ["yes", "y", "true"]
            elif key == "prioritize_space":
                st.session_state.answers["prioritize_space"] = user_msg.strip().lower() in ["yes", "y", "true"]

            # Ack
            ack_obj = chat_acknowledge(key, user_msg, st.session_state.answers) or {}

            # ביטול אימותים עבור מפתחות מסוימים
            if key in NO_CONFIRM_KEYS:
                ack_obj["require_confirm"] = False

            # מדיניות: אם כבר הורדנו חשיבות דלק בגלל <10k, אין צורך לאשר terrain
            if TERRAIN_NO_CONFIRM_IF_LOW_KM and key == "terrain":
                if (st.session_state.answers.get("annual_km") or 0) < 10000:
                    ack_obj["require_confirm"] = False
                    if not ack_obj.get("text"):
                        ack_obj["text"] = "Terrain saved."

            # ניסוחים ידידותיים קצרים למספר מפתחות
            if key == "budget_usd" and st.session_state.answers.get("budget_usd"):
                amt = st.session_state.answers["budget_usd"]
                ack_obj["text"] = f"Great — we’ll look for excellent options around ${amt:,}."
            elif key == "fuel_type" and st.session_state.answers.get("fuel_type"):
                ack_obj["text"] = f"Fuel preference saved: {st.session_state.answers['fuel_type']}."
            elif key == "ownership_years" and st.session_state.answers.get("ownership_years"):
                yrs = st.session_state.answers["ownership_years"]
                extra = " I’ll emphasize long-term reliability." if yrs >= 5 else ""
                ack_obj["text"] = f"Planning to keep the car about {yrs} years.{extra}"
            elif key == "prioritize_safety":
                ack_obj["text"] = "Safety preference saved."
            elif key == "prioritize_space":
                ack_obj["text"] = "Space/size preference saved."

            text = clean_one_line(ack_obj.get("text", ""))

            if text:
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
                    # דילוג על prioritize_mpg אם כבר ענינו עליו
                    while st.session_state.step < len(st.session_state.QUESTIONS):
                        next_key, question = st.session_state.QUESTIONS[st.session_state.step]
                        if next_key == "prioritize_mpg" and st.session_state.answers.get("prioritize_mpg") is not None:
                            st.session_state.step += 1
                            continue
                        st.session_state.chat_messages.append({"role": "assistant", "content": question})
                        st.session_state.awaiting_answer = True
                        break
            st.rerun()

    # show results when done
    if (
        not st.session_state.awaiting_answer
        and not st.session_state.awaiting_yes_no
        and not st.session_state.awaiting_clarification
        and st.session_state.step >= len(st.session_state.QUESTIONS)
        and not st.session_state.results_shown
    ):
        with st.chat_message("assistant"):
            # מציגים רק LLM-summary קצר, ללא Recap כפול
            summary = chat_summary_funny(st.session_state.answers)
            st.write(clean_one_line(summary))
            # advice banner פעם אחת בלבד
            if not st.session_state.advice_shown:
                _advice_banner(st.session_state.answers)
                st.session_state.advice_shown = True
            st.write("Alright, let me crunch the numbers and find your match… 🚗💨")

        payload = dict(st.session_state.answers)
        payload["top_n"] = TOP_SHOW

        result = get_recommendations(payload, catalog_path=CATALOG_PATH)
        items = (result.get("results", []) or [])[:TOP_SHOW]

        if puppeteer_only:
            items = _filter_puppeteer_only(items)

        for it in items:
            src = str(it.get("price_source","")) or ""
            fresh = _freshness_from_source(src)
            if fresh and it.get("price_best"):
                it["price_best"] = f"{it['price_best']} (as of {fresh})"

        with st.chat_message("assistant"):
            if not items:
                st.info("No vehicles matched your filters. Try relaxing constraints.")
            else:
                st.success(f"Found {len(items)} vehicles. Showing top {len(items)}.")
                for i, it in enumerate(items[:TOP_SHOW], start=1):
                    score = as_score(it.get("score"))
                    price = it.get("price_best")
                    src   = it.get("price_source") or "—"
                    year  = it.get("year") or ""
                    year_txt = f"{year} " if year else ""
                    price_txt = f" | {price} • {src}" if price else ""
                    st.markdown(f"**{i}. {year_txt}{it.get('make')} {it.get('model')}** — score {score}{price_txt}")

                    # הסבר אנושי במקום רשימות מספריות
                    explanation = chat_explain_pick(it, st.session_state.answers)
                    with st.expander("Why this pick?"):
                        st.markdown(explanation)

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
        ownership_years = st.number_input("Planned ownership (years)", min_value=1, max_value=15, value=3)

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
            ownership_years=int(ownership_years),
            prioritize_mpg=bool(prioritize_mpg),
            prioritize_safety=bool(prioritize_safety),
            prioritize_space=bool(prioritize_space),
            top_n=TOP_SHOW,
        )

        # advice banner פעם אחת גם ב-Form
        _advice_banner(answers)

        result = get_recommendations(answers, catalog_path=CATALOG_PATH)
        items = (result.get("results", []) or [])[:TOP_SHOW]

        if puppeteer_only:
            items = _filter_puppeteer_only(items)

        for it in items:
            src = str(it.get("price_source","")) or ""
            fresh = _freshness_from_source(src)
            if fresh and it.get("price_best"):
                it["price_best"] = f"{it['price_best']} (as of {fresh})"

        if not items:
            st.info("No vehicles matched your filters. Try relaxing constraints.")
        else:
            import pandas as pd
            def row_map(it):
                d = dict(it)
                d["price_freshness"] = _freshness_from_source(d.get("price_source"))
                return d
            rows = [row_map(it) for it in items]

            cols = [c for c in [
                "year","make","model","option_text","VClass","fuelType",
                "passengers","MPG_comb","overall_safety","Range_mi","electricRange_mi",
                "price_best","price_source","price_freshness","annual_fuel_cost","score"
            ] if rows and c in rows[0]]

            df = pd.DataFrame([{k: r.get(k) for k in cols} for r in rows])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # הורדת CSV
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "Download results as CSV",
                data=csv_buf.getvalue().encode("utf-8"),
                file_name=f"carmatch_results_{dt.date.today().isoformat()}.csv",
                mime="text/csv",
            )

            st.subheader("Why these picks?")
            for i, it in enumerate(items[:TOP_SHOW], start=1):
                explanation = chat_explain_pick(it, answers)
                with st.expander(f"#{i} — {it.get('make')} {it.get('model')} (score {as_score(it.get('score'))})"):
                    st.markdown(explanation)