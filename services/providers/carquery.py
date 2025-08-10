# services/providers/carquery.py
"""
אדפטר ל-CarQuery: חושף פונקציה get_specs(brand, model, year) כפי שהקוד/המבחנים מצפים.
אם קיימת אצלך המחלקה CarQuery תחת services/carquery.py — נשתמש בה.
אם לא, ניפול לפולבאק פשוט דרך HTTP דק.
"""

from typing import Dict, Any, Optional, List

# ננסה להשתמש במחלקה הקיימת שלך אם קיימת:
try:
    from services.carquery import CarQuery  # המחלקה שאתה צירפת בהודעה הקודמת
except Exception:
    CarQuery = None  # fallback למצב שאין את המחלקה

from .http import get_json, Http  # משתמש באותו HTTP שעשינו


def _first(items: Optional[List[dict]]) -> dict:
    if isinstance(items, list) and items:
        return items[0] or {}
    return {}


def _extract_trunk_l(d: Dict[str, Any]) -> Optional[int]:
    """
    CarQuery לא תמיד מחזיר מפתח אחד קבוע לנפח תא מטען.
    ננסה כמה שמות אפשריים. אם אין — נחזיר None.
    """
    candidates = [
        "trunk_l",
        "trunk",                # לפעמים ליטרים או מחרוזת "450 L"
        "luggage_capacity_l",
        "cargo_volume_l",
        "model_trunk",
        "model_cargo_volume",
        "trunk_space",
    ]
    for key in candidates:
        v = d.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
        if isinstance(v, str):
            # ננסה לחלץ מספר מהטקסט ("450 L" → 450)
            num = "".join(ch for ch in v if ch.isdigit())
            if num:
                try:
                    val = int(num)
                    if val > 0:
                        return val
                except ValueError:
                    pass
    return None


def get_specs(brand: str, model: str, year: int) -> Dict[str, Any]:
    """
    מחזיר מילון עם מפתח אופציונלי "trunk_l" אם הצלחנו לזהות.
    אם אין מידע — {}.
    """
    # 1) אם יש לך את המחלקה CarQuery שצירפת — ננסה להשתמש בה:
    if CarQuery is not None:
        cq = CarQuery(http=Http())  # תואם למחלקה שלך שמקבלת Http בבנאי
        try:
            trims = cq.trims(make=brand, model=model, year=year) or []
            first = _first(trims)
            trunk_l = _extract_trunk_l(first)
            return {"trunk_l": trunk_l} if trunk_l is not None else {}
        except Exception:
            # לא מפילים את הזרימה — ננסה פולבאק
            pass

    # 2) פולבאק: קריאת HTTP דקה (המבחנים בדר"כ ממנקי-פאץ' את הקריאה הזו ממילא)
    try:
        params = {"cmd": "getTrims", "make": brand, "model": model, "year": year}
        data = get_json("https://www.carqueryapi.com/api/0.3/", params=params)
        # פורמט נפוץ של CarQuery: {"Trims": [ {...}, {...} ]}
        if isinstance(data, dict):
            items = data.get("Trims") or data.get("trims") or data.get("results") or []
            first = _first(items)
            trunk_l = _extract_trunk_l(first)
            return {"trunk_l": trunk_l} if trunk_l is not None else {}
    except Exception:
        pass

    return {}
