# services/providers/fueleconomy.py
"""
עטיפה דקה למקור נתוני חסכוניות (למשל fueleconomy.gov).
במבחנים אפשר למנקי-פאץ' get_mpg ולהחזיר ערך מספרי (למשל 45).
"""

from typing import Optional
from .http import get_json


def get_mpg(brand: str, model: str, year: int) -> Optional[float]:
    """
    מחזיר MPG משולב (ערך יחיד), או None אם אין נתון.
    """
    params = {"make": brand, "model": model, "year": year}
    data = get_json("https://api.fueleconomy.example/mpg", params=params)

    # מפתחות נפוצים: "mpg_combined" / "combined_mpg" / "mpg"
    if isinstance(data, dict):
        for k in ("mpg_combined", "combined_mpg", "mpg"):
            v = data.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return float(v)

        # לפעמים יש nested
        res = data.get("result") or data.get("data")
        if isinstance(res, dict):
            for k in ("mpg_combined", "combined_mpg", "mpg"):
                v = res.get(k)
                if isinstance(v, (int, float)) and v > 0:
                    return float(v)

    return None
