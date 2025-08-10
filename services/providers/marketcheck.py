# services/providers/marketcheck.py
from typing import List, Any, Dict, Optional

from domain.car import Car
from domain.user_profile import UserProfile
from . import http  # חשוב: מייבאים את המודול, כדי ש-monkeypatch יתפוס


def _to_int(v: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if v is None:
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _to_float(v: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _map_item_to_car(it: Dict[str, Any]) -> Car:
    brand = it.get("make") or it.get("brand") or ""
    model = it.get("model") or ""
    year = _to_int(it.get("year")) or _to_int(it.get("build", {}).get("year")) or 0
    price = _to_int(it.get("price")) or _to_int(it.get("msrp")) or 0
    body = it.get("body_type") or it.get("body") or it.get("build", {}).get("body_type") or ""
    seats = _to_int(it.get("seats")) or _to_int(it.get("build", {}).get("doors")) or 5
    trunk_l = _to_int(it.get("trunk_l"))
    vin = it.get("vin")

    comfort_score = _to_float(it.get("comfort_score"))
    efficiency_score = _to_float(it.get("efficiency_score"))
    driving_fun_score = _to_float(it.get("driving_fun_score"))

    features = None
    if isinstance(it.get("features"), list):
        features = [str(x) for x in it["features"]]

    cid = str(it.get("id") or vin or f"{brand}-{model}-{year}-{price}")

    powertrain = (it.get("powertrain")
                  or it.get("fuel_type")
                  or it.get("build", {}).get("fuel_type")
                  or "gas")
    pt = str(powertrain).lower()
    if "diesel" in pt:
        powertrain_norm = "diesel"
    elif "hybrid" in pt and "plug" in pt:
        powertrain_norm = "phev"
    elif "hybrid" in pt:
        powertrain_norm = "hybrid"
    elif pt in ("ev", "electric"):
        powertrain_norm = "ev"
    else:
        powertrain_norm = "gas"

    url = it.get("vdp_url") or it.get("url")

    return Car(
        id=cid,
        brand=str(brand),
        model=str(model),
        year=year,
        price=price,
        powertrain=powertrain_norm,
        body=str(body),
        seats=seats,
        trunk_l=trunk_l,
        comfort_score=comfort_score,
        efficiency_score=efficiency_score,
        driving_fun_score=driving_fun_score,
        source="yad2",  # או "marketcheck" אם תרצה
        url=url,
        features=features,
    )


def search(profile: UserProfile) -> List[Car]:
    params = {
        "budget_max": profile.budget,
        "seats_min": profile.passengers,
        "usage": profile.usage,
        "terrain": profile.terrain,
        "condition": profile.new_or_used,
        "limit": 50,
    }

    data = http.get_json("https://api.marketcheck.com/v2/search/cars", params=params)

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("list", "results", "cars", "data"):
            if isinstance(data.get(key), list):
                items = data[key]
                break

    return [_map_item_to_car(it) for it in items]
