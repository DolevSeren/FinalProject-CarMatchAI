# services/carquery.py
"""
גשר תאימות:
    from services.carquery import CarQuery
וגם מייצא פונקציה get_specs מה-provider.
"""
from typing import Optional, List, Dict, Any
from .providers.http import Http
from .providers.carquery import get_specs as _get_specs

BASE = "https://www.carqueryapi.com/api/0.3/"

class CarQuery:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    # שמירה על ה-API הישן שלך (אם יש קוד שמסתמך עליו)
    def makes(self) -> List[Dict[str, Any]]:
        r = self.http.get_json(BASE, params={"cmd": "getMakes", "sold_in_us": "1"})
        return r.get("Makes", [])

    def models(self, make: str, year: int | None = None) -> List[Dict[str, Any]]:
        params = {"cmd": "getModels", "make": make}
        if year: params["year"] = year
        r = self.http.get_json(BASE, params=params)
        return r.get("Models", [])

    def trims(self, make: str, model: str, year: int | None = None) -> List[Dict[str, Any]]:
        params = {"cmd": "getTrims", "make": make, "model": model}
        if year: params["year"] = year
        r = self.http.get_json(BASE, params=params)
        return r.get("Trims", [])

# פונקציה ברמת מודול – להתאמה למה שהmatcher משתמש
def get_specs(brand: str, model: str, year: int):
    return _get_specs(brand, model, year)
