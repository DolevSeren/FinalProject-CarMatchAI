# agent/providers.py
from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path
import json

from matching.domain import CarModel

class CarDataProvider(ABC):
    @abstractmethod
    def fetch(self) -> List[CarModel]:
        ...

class GlobalAPIProvider(CarDataProvider):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def fetch(self) -> List[CarModel]:
        """
        טוען את data/models_sample.json במבנה הרזה שהבאת
        ומשלים שדות חסרים (powertrain/מחירים/ניקוד) בצורה הגיונית כדי שהאפליקציה תרוץ.
        כשתחבר API אמיתי – תחליף את החלקים של המחירים/ניקוד.
        """
        sample_path = Path(__file__).resolve().parents[1] / "data" / "models_sample.json"
        with open(sample_path, "r", encoding="utf-8") as f:
            raw: List[Dict] = json.load(f)

        cars: List[CarModel] = []
        for r in raw:
            make = r.get("make")
            model = r.get("model")
            year = int(r.get("year"))
            body = r.get("body")

            # קביעה אוטומטית של סוג הנעה לפי הדגם/מותג
            powertrain = self._infer_powertrain(make, model)

            # ניקוד בסיסי לפי סגמנט, עם התאמות קלות לפי הנעה
            comfort, handling, efficiency = self._baseline_scores(body, powertrain)

            # הערכת מחיר חדש ומשומש כדי שהסינון/דירוג יעבדו
            price_new = self._estimate_new_price(make, model, body, powertrain)
            price_used = round(price_new * 0.85)  # הנחת דמו: 2024 "משומש קל" ~15% פחות

            cars.append(CarModel(
                make=make,
                model=model,
                year_from=year,
                year_to=None,
                body_style=body,
                powertrain=powertrain,
                seats=None,
                cargo_l=None,
                comfort_score=comfort,
                handling_score=handling,
                efficiency_score=efficiency,
                price_new_usd=price_new,
                price_used_usd=price_used,
                meta={"drivetrain": self._infer_drivetrain(make, model), "seating_height": "normal"},
            ))
        return cars

    # ---------- Heuristics / helpers ----------

    def _infer_powertrain(self, make: str, model: str) -> str | None:
        name = f"{make} {model}".lower()
        if "tesla" in name or "i4" in name or "ioniq 6" in name or "leaf" in name:
            return "BEV"
        if "prius" in name:
            return "HEV"
        return "ICE"  # ברירת־מחדל

    def _infer_drivetrain(self, make: str, model: str) -> str:
        name = f"{make} {model}".lower()
        # פשטות: רוב הדגמים כאן הם FWD, ספורט/פרימיום RWD
        if any(k in name for k in ["mustang", "mx-5", "gr86", "bmw", "mercedes", "audi", "gti"]):
            return "RWD"
        return "FWD"

    def _baseline_scores(self, body: str, powertrain: str | None):
        # ניקוד בסיסי לפי מרכב
        body = (body or "").lower()
        comfort = {"sedan": 0.70, "hatchback": 0.65, "coupe": 0.60, "convertible": 0.58}.get(body, 0.65)
        handling = {"sedan": 0.62, "hatchback": 0.65, "coupe": 0.80, "convertible": 0.78}.get(body, 0.62)
        efficiency = {"sedan": 0.70, "hatchback": 0.75, "coupe": 0.55, "convertible": 0.53}.get(body, 0.68)

        # התאמות לפי סוג הנעה
        if powertrain == "BEV":
            efficiency = max(efficiency, 0.85)
            handling += 0.03  # מרכז כובד נמוך
        elif powertrain == "HEV":
            efficiency = max(efficiency, 0.80)

        return round(comfort, 2), round(handling, 2), round(efficiency, 2)

    def _estimate_new_price(self, make: str, model: str, body: str, powertrain: str | None) -> int:
        name = f"{make} {model}".lower()
        # מחירי דמו סבירים כדי שה־UI יעבוד (לא נתונים אמיתיים)
        table = {
            "toyota corolla": 23000, "toyota camry": 31000, "toyota prius": 28000, "toyota gr86": 29000,
            "honda civic": 24000, "honda accord": 31000,
            "hyundai elantra": 22000, "hyundai sonata": 28000, "hyundai ioniq 6": 43000,
            "kia forte": 21000, "kia k5": 27000,
            "mazda mazda3": 25000, "mazda mx-5": 30000,
            "nissan sentra": 21000, "nissan altima": 28000, "nissan leaf": 29000,
            "subaru impreza": 24000, "subaru legacy": 29000,
            "volkswagen jetta": 22000, "volkswagen golf gti": 32000,
            "ford mustang": 32000,
            "bmw 330i": 45500, "bmw i4": 53000,
            "mercedes-benz c-class": 46000, "mercedes-benz e-class": 58000,
            "audi a4": 45000, "audi a6": 57000,
            "tesla model 3": 40000,
            "volvo s60": 43000,
        }
        base = table.get(name)
        if base:
            return int(base)

        # נפילה למקרה שלא מצא: הערכה לפי סגמנט/הנעה
        segment_base = {
            "sedan": 27000, "hatchback": 24000, "coupe": 30000, "convertible": 32000
        }.get((body or "").lower(), 26000)
        if powertrain == "BEV":
            segment_base += 12000
        return int(segment_base)
