# services/matching/matcher.py
from typing import List

from domain.user_profile import UserProfile
from domain.car import Car

# ייבוא ישיר מ- providers (איפה שה-APIים שלך)
import services.providers.marketcheck as marketcheck
import services.providers.carquery as carquery
import services.providers.fueleconomy as fueleconomy
import services.providers.nhtsa_recalls as nhtsa_recalls
import services.providers.nhtsa_safety as nhtsa_safety  # לשימוש עתידי אם תרצה
import services.providers.vpic as vpic


def _score(car: Car, profile: UserProfile) -> float:
    score = 0.0
    if getattr(car, "seats", None) is not None and car.seats >= profile.passengers:
        score += 1.0
    musts = set(profile.must_haves or [])
    if "efficiency" in musts and getattr(car, "efficiency_score", None) is not None:
        score += float(car.efficiency_score)
    if "comfort" in musts and getattr(car, "comfort_score", None) is not None:
        score += float(car.comfort_score)
    if "driving_fun" in musts and getattr(car, "driving_fun_score", None) is not None:
        score += float(car.driving_fun_score)
    if profile.terrain == "hilly" and getattr(car, "driving_fun_score", None) is not None:
        score += 0.3 * float(car.driving_fun_score)
    return score


def _enrich(car: Car) -> Car:
    try:
        vin = getattr(car, "vin", None)
        if vin:
            v = vpic.decode_vin(vin)
            if v and "features" in v:
                car.features = (car.features or []) + v["features"]
    except Exception:
        pass

    try:
        specs = carquery.get_specs(car.brand, car.model, car.year)
        if specs and specs.get("trunk_l") and not getattr(car, "trunk_l", None):
            car.trunk_l = specs["trunk_l"]
    except Exception:
        pass

    try:
        mpg = fueleconomy.get_mpg(car.brand, car.model, car.year)
        if mpg:
            car.efficiency_score = max(0.0, min(10.0, float(mpg) / 5.0))
    except Exception:
        pass

    try:
        recs = nhtsa_recalls.get_recalls(car.brand, car.model, car.year)
        if recs is not None:
            car.features = (car.features or []) + [f"recalls:{len(recs)}"]
    except Exception:
        pass

    return car


def match(profile: UserProfile, limit: int = 10) -> List[Car]:
    cars: List[Car] = []

    if profile.new_or_used in ("used", "any"):
        cars.extend(marketcheck.search(profile))

    # NEW → כשתחבר ספק ליבואנים תוסיף כאן

    def _ok(c: Car) -> bool:
        return (
            getattr(c, "price", None) is not None and c.price <= profile.budget
            and getattr(c, "seats", None) is not None and c.seats >= profile.passengers
        )

    cars = [c for c in cars if _ok(c)]
    cars = [_enrich(c) for c in cars]
    cars = sorted(cars, key=lambda c: _score(c, profile), reverse=True)
    return cars[:limit]
