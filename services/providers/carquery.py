# services/providers/carquery.py
from typing import Dict, Any, Optional, List
from . import http  # חשוב: מייבאים את המודול

def _first(items: Optional[List[dict]]) -> dict:
    if isinstance(items, list) and items:
        return items[0] or {}
    return {}

def _extract_trunk_l(d: Dict[str, Any]) -> Optional[int]:
    candidates = [
        "trunk_l", "trunk", "luggage_capacity_l", "cargo_volume_l",
        "model_trunk", "model_cargo_volume", "trunk_space",
    ]
    for key in candidates:
        v = d.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
        if isinstance(v, str):
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
    try:
        params = {"cmd": "getTrims", "make": brand, "model": model, "year": year}
        data = http.get_json("https://www.carqueryapi.com/api/0.3/", params=params)
        if isinstance(data, dict):
            items = data.get("Trims") or data.get("trims") or data.get("results") or []
            first = _first(items)
            trunk_l = _extract_trunk_l(first)
            return {"trunk_l": trunk_l} if trunk_l is not None else {}
    except Exception:
        pass
    return {}
