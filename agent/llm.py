# agent/llm.py
# English-only output; Hebrew comments allowed in code.

from typing import Dict, Optional

# ---------- Small helpers ----------

def _fmt_usd(n: Optional[int]) -> str:
    try:
        return f"${int(n):,}"
    except Exception:
        return "$0"

def _bool(a, key: str, default: bool = False) -> bool:
    v = a.get(key, default)
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y"}

def _clean(s: Optional[str]) -> str:
    return " ".join((s or "").split())


# ---------- Conversational acks (deterministic – no LLM calls) ----------

def chat_acknowledge(answer_key: str, user_text: str, answers_snapshot: Dict) -> Dict:
    """
    Returns dict:
      {
        "text": str,
        "require_confirm": bool,
        "confirm_text": Optional[str],
        "skip": bool
      }
    All messages are in English only.
    """
    key = (answer_key or "").strip().lower()
    val_raw = _clean(user_text)
    a = answers_snapshot or {}

    # condition
    if key == "condition":
        cond = (a.get("condition") or "any").lower()
        if cond == "any":
            return {"text": "Choosing ‘any’ is great — it keeps your options wide open!",
                    "require_confirm": False, "confirm_text": None, "skip": False}
        pretty = cond.capitalize()
        return {"text": f"You prefer {pretty}.",
                "require_confirm": True, "confirm_text": "Did I get that right? (yes/no)", "skip": False}

    # budget (always positive tone)
    if key == "budget_usd":
        budget = a.get("budget_usd")
        return {"text": f"Great — we’ll look for excellent options around {_fmt_usd(budget)}.",
                "require_confirm": False, "confirm_text": None, "skip": False}

    # fuel type
    if key == "fuel_type":
        return {"text": f"Fuel preference saved: {a.get('fuel_type')}.",
                "require_confirm": False, "confirm_text": None, "skip": False}

    # passengers
    if key == "passengers":
        try:
            p = int(a.get("passengers"))
        except Exception:
            p = None
        if p is not None and p >= 1:
            msg = "If you rarely carry many people, cabin space likely isn’t a top priority."
            return {"text": msg, "require_confirm": True,
                    "confirm_text": "Did I understand that correctly? (yes/no)", "skip": False}
        return {"text": f"Passengers: {val_raw}.",
                "require_confirm": True, "confirm_text": "Did I get that right? (yes/no)", "skip": False}

    # annual_km (statement, no confirm)
    if key == "annual_km":
        km = a.get("annual_km")
        if km is None:
            text = "Kilometer usage not specified — we’ll treat it as average (10k–20k km/yr)."
        elif 0 <= km <= 10000:
            text = "You drive very little (0–10k km/yr), so fuel economy likely isn’t critical."
        elif 10000 < km <= 20000:
            text = "You drive an average amount (10k–20k km/yr); we’ll balance economy and performance."
        else:
            text = "You drive a lot (20k+ km/yr); fuel economy and comfort on long trips matter more."
        return {"text": text, "require_confirm": False, "confirm_text": None, "skip": False}

    # terrain
    if key == "terrain":
        terrain = (a.get("terrain") or "").lower()
        if terrain == "flat":
            return {"text": "On flat routes, unless you’re a performance enthusiast, we’ll emphasize fuel economy.",
                    "require_confirm": True, "confirm_text": "Am I right? (yes/no)", "skip": False}
        if terrain == "hilly":
            return {"text": "Hilly terrain noted — torque and braking performance matter more.",
                    "require_confirm": True, "confirm_text": "Did I get that right? (yes/no)", "skip": False}
        return {"text": "Terrain not specified — we’ll assume mixed conditions.",
                "require_confirm": True, "confirm_text": "Should we assume mixed terrain? (yes/no)", "skip": False}

    # ownership years (short, positive; confirm not needed)
    if key == "ownership_years":
        yrs = a.get("ownership_years")
        extra = " I’ll emphasize long-term reliability." if (yrs or 0) >= 5 else ""
        return {"text": f"Planning to keep the car about {yrs} years.{extra}",
                "require_confirm": False, "confirm_text": None, "skip": False}

    # prioritize flags — concise, no confirm needed from the UI layer (it can override)
    if key == "prioritize_safety":
        return {"text": "Safety preference saved.", "require_confirm": False, "confirm_text": None, "skip": False}
    if key == "prioritize_space":
        return {"text": "Space/size preference saved.", "require_confirm": False, "confirm_text": None, "skip": False}
    if key == "prioritize_mpg":
        pref = str(a.get("prioritize_mpg")).lower() in {"true", "yes", "y"}
        return {"text": "Efficiency preference saved." if pref else "Efficiency de-emphasized.",
                "require_confirm": False, "confirm_text": None, "skip": False}

    # default
    return {"text": f"{answer_key.replace('_', ' ').capitalize()}: {val_raw}.",
            "require_confirm": True, "confirm_text": "Did I get that right? (yes/no)", "skip": False}


def chat_clarify_no(answer_key: str, answers_snapshot: Dict) -> str:
    """Short, neutral correction prompt (English-only)."""
    return "Please share a brief correction so I can fix it."


def chat_summary_funny(answers_snapshot: Dict) -> str:
    """Short, friendly summary (English-only)."""
    a = answers_snapshot or {}
    parts = []

    budget = a.get("budget_usd")
    if budget:
        parts.append(f"budget ~{_fmt_usd(budget)}")

    cond = a.get("condition")
    if cond:
        parts.append(f"condition: {cond}")

    pax = a.get("passengers")
    if pax:
        parts.append(f"{pax} passengers")

    km = a.get("annual_km")
    if km is not None:
        parts.append(f"~{km:,} km/yr")

    terrain = a.get("terrain")
    if terrain:
        parts.append(f"terrain: {terrain}")

    yrs = a.get("ownership_years")
    if yrs:
        parts.append(f"keep ~{yrs} years")

    needs = a.get("special_needs") or []
    if needs:
        parts.append("needs: " + ", ".join(needs))
    else:
        parts.append("no special needs")

    line = ", ".join(parts)
    return f"Got it: {line}. Let’s find great matches that fit the plan."


# ---------- Human-friendly explanation for each pick ----------

def chat_explain_pick(item: Dict, answers_snapshot: Dict) -> str:
    """
    Returns a short, human paragraph (no bullet points, no raw numbers) that
    explains why this specific vehicle fits the user's answers.
    English-only. Deterministic (no external LLM call).
    """
    a = answers_snapshot or {}
    mk, md = item.get("make"), item.get("model")
    year = item.get("year")
    title = f"{year} {mk} {md}".strip() if year else f"{mk} {md}".strip()

    pax = a.get("passengers")
    km = a.get("annual_km")
    yrs = a.get("ownership_years")
    bud = a.get("budget_usd")
    fuel = (item.get("fuelType") or "").lower()

    # Preferences
    want_eff  = _bool(a, "prioritize_mpg", True)
    want_safe = _bool(a, "prioritize_safety", True)
    want_space = _bool(a, "prioritize_space", False)

    bits = []

    # Opening line — friendly and at eye-level
    bits.append(f"{title} fits what you asked for.")

    # Space / passengers
    if pax:
        if pax <= 2 and not want_space:
            bits.append("It’s the right size for your day-to-day — easy to live with without wasting space.")
        elif pax >= 5 or want_space:
            bits.append("It offers the room you’ll need when the whole crew rides along.")
        else:
            bits.append("Cabin space should suit your usual rides comfortably.")

    # Annual mileage → fuel emphasis
    if km is not None:
        if km < 10000:
            bits.append("Because you don’t drive much, we didn’t chase extreme fuel economy and focused on overall value and comfort.")
        elif km >= 20000:
            bits.append("Since you drive a lot, it balances comfort with solid efficiency to keep running costs sensible.")
        else:
            bits.append("With typical yearly mileage, it balances efficiency and performance naturally.")

    # Fuel type nuance
    if "electric" in fuel and "gas" not in fuel:
        bits.append("Being fully electric, it’s quiet and smooth — great for daily use and lower running costs.")
    elif "gas" in fuel and "electric" in fuel:
        bits.append("As a plug-in hybrid, you can do short trips on electricity with gasoline backup for longer journeys.")
    elif "diesel" in fuel:
        bits.append("Diesel torque helps with relaxed cruising and stronger pull when loaded.")

    # Safety preference
    if want_safe:
        bits.append("Safety is a priority here, so we kept models with a strong record and modern driver-assist tech.")

    # Reliability / ownership length
    if yrs and yrs >= 5:
        bits.append("You plan to keep the car for years, so we emphasized reputation for long-term reliability.")

    # Budget note — always positive
    if bud:
        bits.append(f"And importantly, it lines up with your budget around {_fmt_usd(bud)}.")

    # Closing
    bits.append("Overall, it’s a sensible, low-stress match for your needs — and we can nudge the shortlist toward more performance, space, or features if you want.")

    paragraph = " ".join(bits)
    return _clean(paragraph)