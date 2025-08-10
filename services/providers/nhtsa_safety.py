# services/providers/nhtsa_safety.py
from typing import Dict, Any
from . import http  # חשוב

def get_safety_ratings(brand: str, model: str, year: int) -> Dict[str, Any]:
    params = {"make": brand, "model": model, "modelYear": year}
    data = http.get_json("https://api.nhtsa.gov/SafetyRatings", params=params)
    if isinstance(data, dict):
        return data
    return {}
