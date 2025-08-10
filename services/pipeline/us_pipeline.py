from typing import List, Dict, Any, Optional
from ..fueleconomy import FuelEconomy
from ..nhtsa_safety import NhtsaSafety
from ..nhtsa_recalls import NhtsaRecalls
from ..marketcheck import Marketcheck
from ..http import Http
from ..cache import DiskCache

def _norm(s: str) -> str:
    return (s or "").strip().lower()

class USPipeline:
    def __init__(self, http: Http | None = None, cache: DiskCache | None = None,
                 marketcheck: Optional[Marketcheck] = None):
        self.http = http or Http()
        self.fe = FuelEconomy(self.http)
        self.safety = NhtsaSafety(self.http)
        self.recalls = NhtsaRecalls(self.http)
        self.cache = cache or DiskCache()
        self.marketcheck = marketcheck  # יוזם רק אם יש API key

    # ----- Lists -----
    def list_makes(self, year: int) -> List[str]:
        key = f"makes:{year}"
        cached = self.cache.get(key)
        if cached is not None: return cached
        makes = sorted(self.fe.menu_makes(year))
        self.cache.set(key, makes)
        return makes

    def list_models(self, year: int, make: str) -> List[str]:
        key = f"models:{year}:{make}"
        cached = self.cache.get(key)
        if cached is not None: return cached
        models = sorted(self.fe.menu_models(year, make))
        self.cache.set(key, models)
        return models

    # ----- Vehicles + Safety -----
    def vehicles_with_safety(self, year: int, make: str, model: str) -> List[Dict[str, Any]]:
        key = f"veh:{year}:{make}:{model}"
        cached = self.cache.get(key)
        if cached is not None: return cached

        options = self.fe.menu_options(year, make, model)
        out: List[Dict[str, Any]] = []

        try:
            safety_models = { _norm(m): m for m in self.safety.models(year, make) }
        except Exception:
            safety_models = {}

        for opt in options:
            vid = int(opt.get("value"))
            veh = self.fe.vehicle(vid)
            overall = None
            try:
                if _norm(model) in safety_models:
                    variants = self.safety.variants(year, make, safety_models[_norm(model)])
                    if variants:
                        nhtsa_vid = variants[0].get("VehicleId")
                        rating = self.safety.rating_by_vehicle_id(nhtsa_vid)
                        if isinstance(rating, dict):
                            if "OverallRating" in rating:
                                overall = rating.get("OverallRating")
                            else:
                                res = rating.get("Results") or []
                                if res and isinstance(res, list):
                                    overall = res[0].get("OverallRating")
            except Exception:
                pass

            out.append({
                "year": year,
                "make": make,
                "model": model,
                "option_text": opt.get("text"),
                "fueleconomy": veh,
                "overall_safety": overall,
                "vehicle_id": vid,
            })

        self.cache.set(key, out)
        return out

    # ----- Used prices via Marketcheck -----
    def used_price_summary(self, make: str, model: str, year: int | None,
                           zip_code: int | None, radius: int = 50) -> Optional[Dict[str, Any]]:
        """
        מחזיר סטטיסטיקות מחיר ליד‑2 (min/median/avg/max + sample) אם קיים מפתח Marketcheck.
        """
        if not self.marketcheck:
            return None
        key = f"mc:{year}:{make}:{model}:{zip_code}:{radius}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        res = self.marketcheck.search_used(make=make, model=model, year=year,
                                           zip_code=zip_code, radius=radius, rows=50)
        summary = self.marketcheck.summarize_listings(res)
        self.cache.set(key, summary)
        return summary
