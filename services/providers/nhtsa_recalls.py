# services/providers/nhtsa_recalls.py
"""
NHTSA Recalls – שליפת ריקולים לדגם/שנה. במבחנים ניתן למנקי-פאץ' להחזיר []
"""

from typing import List, Dict, Any
from .http import get_json


def get_recalls(brand: str, model: str, year: int) -> List[Dict[str, Any]]:
    """
    מחזיר רשימת ריקולים (יכול להיות ריקה). כל פריט במבנה מילון חופשי.
    """
    params = {"make": brand, "model": model, "modelYear": year}
    data = get_json("https://api.nhtsa.gov/recalls/recallsByVehicle", params=params)

    if isinstance(data, dict):
        # מפתחות נפוצים: "results", "Results", "recalls"
        for key in ("results", "Results", "recalls"):
            v = data.get(key)
            if isinstance(v, list):
                return v

    if isinstance(data, list):
        return data

    return []
