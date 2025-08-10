# services/providers/nhtsa_recalls.py
from typing import List, Dict, Any
from . import http  # חשוב

def get_recalls(brand: str, model: str, year: int) -> List[Dict[str, Any]]:
    params = {"make": brand, "model": model, "modelYear": year}
    data = http.get_json("https://api.nhtsa.gov/recalls/recallsByVehicle", params=params)
    if isinstance(data, dict):
        for key in ("results", "Results", "recalls"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    if isinstance(data, list):
        return data
    return []
