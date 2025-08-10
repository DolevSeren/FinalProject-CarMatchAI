# services/providers/fueleconomy.py
from typing import Optional
from . import http  # חשוב

def get_mpg(brand: str, model: str, year: int) -> Optional[float]:
    data = http.get_json("https://api.fueleconomy.example/mpg", params={"make": brand, "model": model, "year": year})
    if isinstance(data, dict):
        for k in ("mpg_combined", "combined_mpg", "mpg"):
            v = data.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return float(v)
        res = data.get("result") or data.get("data")
        if isinstance(res, dict):
            for k in ("mpg_combined", "combined_mpg", "mpg"):
                v = res.get(k)
                if isinstance(v, (int, float)) and v > 0:
                    return float(v)
    return None
