# agent/llm.py
# English-only output; # הערות בעברית מותרות בקוד
from typing import Dict, Optional

# אין כאן קריאה ל-LLM עבור ה-Ack — הכל דטרמיניסטי לפי כללים ותבניות
# זה מבטיח ניסוח מדויק כמו שביקשת, בלי "Hey" ובלי שאלות מיותרות.

def _fmt_usd(n: Optional[int]) -> str:
    try:
        return f"${int(n):,}"
    except Exception:
        return "$0"

def chat_acknowledge(answer_key: str, user_text: str, answers_snapshot: Dict) -> Dict:
    """
    Returns dict:
      {
        "text": str,                 # הודעת Ack תמציתית
        "require_confirm": bool,     # האם להציג (yes/no)
        "confirm_text": Optional[str], # אם יש נוסח מותאם לשאלת האישור
        "skip": bool                 # לדלג לגמרי על הודעת Ack (למשל comfort=no)
      }
    כל ההודעות באנגלית בלבד. # אפשר להחליף לנוסח אחר כאן לפי הצורך.
    """
    key = (answer_key or "").strip().lower()
    val_raw = (user_text or "").strip()
    a = answers_snapshot or {}

    # ------- condition -------
    if key == "condition":
        cond = (a.get("condition") or "any").lower()
        if cond == "any":
            # כמו הדוגמה שלך: ללא אישור, הודעת עידוד
            return {
                "text": "Choosing ‘any’ is great — it keeps your options wide open!",
                "require_confirm": False,
                "confirm_text": None,
                "skip": False,
            }
        else:
            # new/used — אפשר לאשר
            pretty = cond.capitalize()
            return {
                "text": f"You prefer {pretty}.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }

    # ------- budget_usd -------
    if key == "budget_usd":
        budget = a.get("budget_usd")
        return {
            # "וואו זה תקציב מעולה! נוכל למצוא הרבה רכבים שיתאימו לך."
            "text": f"Nice budget! We can find plenty of great cars around {_fmt_usd(budget)}.",
            "require_confirm": False,
            "confirm_text": None,
            "skip": False,
        }

    # ------- passengers -------
    if key == "passengers":
        passengers = a.get("passengers")
        # ניסוח מאשש + שאלה מותאמת
        if isinstance(passengers, int) and passengers >= 1:
            return {
                # "זאת אומרת שמרווח ברכב זה לא משהו שמאוד חשוב..." עם אישור
                "text": "If you rarely carry many people, cabin space likely isn’t a top priority.",
                "require_confirm": True,
                "confirm_text": "Did I understand that correctly? (yes/no)",
                "skip": False,
            }
        else:
            # ערך לא תקין — נבקש אישור כללי
            return {
                "text": f"Passengers: {val_raw}.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }

    # ------- annual_km -------
    if key == "annual_km":
        km = a.get("annual_km")
        # לפי הדוגמה שלך: הצהרה ללא אישור, כולל טווחים
        if km is None:
            text = "Kilometer usage not specified — we’ll treat it as average (10k–20k km/yr)."
        elif 0 <= km <= 10000:
            text = "You drive very little (0–10k km/yr), so fuel economy likely isn’t critical."
        elif 10000 < km <= 20000:
            text = "You drive an average amount (10k–20k km/yr); we’ll balance economy and performance."
        else:
            text = "You drive a lot (20k+ km/yr); fuel economy and comfort on long trips matter more."
        return {
            "text": text,
            "require_confirm": False,   # ללא אישור לפי הדוגמה שלך
            "confirm_text": None,
            "skip": False,
        }

    # ------- terrain -------
    if key == "terrain":
        terrain = (a.get("terrain") or "").lower()
        if terrain == "flat":
            # "אלא אם אתה חובב ביצועים... האם אני צודק? כן/לא?"
            return {
                "text": "On flat routes, unless you’re a performance enthusiast, we’ll emphasize fuel economy.",
                "require_confirm": True,
                "confirm_text": "Am I right? (yes/no)",
                "skip": False,
            }
        elif terrain == "hilly":
            return {
                "text": "Hilly terrain noted — torque and braking performance matter more.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }
        else:
            return {
                "text": "Terrain not specified — we’ll assume mixed conditions.",
                "require_confirm": True,
                "confirm_text": "Should we assume mixed terrain? (yes/no)",
                "skip": False,
            }

    # ------- comfort_priority -------
    if key == "comfort_priority":
        # לפי הבקשה שלך: אם התשובה היא no — לא צריך את השורה הזו (דלג)
        is_yes = str(val_raw).strip().lower() in ["yes", "y", "true", "1"]
        if not is_yes:
            return {"text": "", "require_confirm": False, "confirm_text": None, "skip": True}
        # אם כן — אפשר לתת אישור קצר
        return {
            "text": "Comfort is a priority — noted.",
            "require_confirm": True,
            "confirm_text": "Did I get that right? (yes/no)",
            "skip": False,
        }

    # ------- fun_priority -------
    if key == "fun_priority":
        is_yes = str(val_raw).strip().lower() in ["yes", "y", "true", "1"]
        if is_yes:
            # אתה אמרת שזה “סבבה” — נשאיר אישור
            return {
                "text": "Got it — fun to drive matters more than efficiency.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }
        else:
            return {
                "text": "Efficiency will take priority over driving excitement.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }

    # ------- years_to_keep -------
    if key == "years_to_keep":
        years = a.get("years_to_keep")
        return {
            "text": f"Planning to keep the car ~{years} years — we’ll focus on sporty yet reliable picks within budget.",
            "require_confirm": False,
            "confirm_text": None,
            "skip": False,
        }

    # ------- special_needs -------
    if key == "special_needs":
        needs = a.get("special_needs") or []
        if not needs:
            # הדגשת העדר צרכים מיוחדים — בלי אישור
            return {
                "text": "No special needs — that keeps choices simple.",
                "require_confirm": False,
                "confirm_text": None,
                "skip": False,
            }
        else:
            return {
                "text": f"Special needs noted: {', '.join(needs)}.",
                "require_confirm": True,
                "confirm_text": "Did I get that right? (yes/no)",
                "skip": False,
            }

    # ברירת מחדל
    return {
        "text": f"{answer_key.replace('_', ' ').capitalize()}: {val_raw}.",
        "require_confirm": True,
        "confirm_text": "Did I get that right? (yes/no)",
        "skip": False,
    }

def chat_clarify_no(answer_key: str, answers_snapshot: Dict) -> str:
    """
    English-only, one short sentence asking for brief correction after NO.
    """
    # # נוסח קצר וענייני
    return "Please share a brief correction so I can fix it."

def chat_summary_funny(answers_snapshot: Dict) -> str:
    """
    Short, friendly summary (English-only).
    """
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

    if a.get("comfort_priority") is True:
        parts.append("comfort-priority")
    elif a.get("comfort_priority") is False:
        parts.append("comfort not a priority")

    if a.get("fun_priority") is True:
        parts.append("fun > efficiency")
    elif a.get("fun_priority") is False:
        parts.append("efficiency > fun")

    years = a.get("years_to_keep")
    if years:
        parts.append(f"keep ~{years} years")

    needs = a.get("special_needs") or []
    if needs:
        parts.append("needs: " + ", ".join(needs))
    else:
        parts.append("no special needs")

    line = ", ".join(parts)
    return f"Got it: {line}. Let’s find lively, reliable options that fit the plan."
