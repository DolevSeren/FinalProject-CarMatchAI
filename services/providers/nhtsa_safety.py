# services/providers/nhtsa_safety.py
"""
בטיחות NHTSA – לא חובה לשימוש כעת, בנוי להרחבה עתידית.
"""

from typing import Dict, Any
from .http import get_json


def get_safety_ratings(brand: str, model: str, year: int) -> Dict[str, Any]:
    """
    מחזיר מילון עם דירוגי בטיחות אם קיימים, אחרת {}.
    """
    params = {"make": brand, "model": model, "modelYear": year}
    data = get_json("https://api.nhtsa.gov/SafetyRatings", params=params)

    if isinstance(data, dict):
        # נחזיר את מה שיש ללא עיבוד כבד – במבחנים אפשר למנקי-פאץ' ולהחזיר מבנה נוח
        return data

    return {}
