# matching/matcher.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional ,Tuple
from matching.domain import CarModel, UserProfile

@dataclass
class UserProfile:
    new_or_used: str
    usage: str
    typical_passengers: int
    annual_km: int
    road_type: str
    budget_usd: Optional[int]
    current_car_likes: List[str]
    current_car_dislikes: List[str]
    ownership_years: int
    special_needs: List[str]

def derive_weights(profile: UserProfile) -> Dict[str, float]:
    w = {"efficiency":0.22,"comfort":0.20,"safety":0.22,"reliability":0.16,"space":0.10,"performance":0.10}
    if profile.typical_passengers >= 5:
        w["space"] += 0.06; w["safety"] += 0.04; w["performance"] -= 0.05; w["efficiency"] -= 0.05
    if profile.ownership_years >= 6:
        w["reliability"] += 0.06; w["performance"] -= 0.03; w["efficiency"] -= 0.03
    s = sum(w.values())
    return {k:v/s for k,v in w.items()}

def score_snapshot(snap: Dict[str, Any], w: Dict[str, float]) -> float:
    # שדות 0..1 בדמו; כשנעבור ללייב ננרמל אמיתי
    eff = snap.get("efficiency_score", 0.5)
    com = snap.get("comfort_score", 0.5)
    saf = snap.get("safety_score", 0.5)
    rel = snap.get("reliability_score", 0.5)
    spa = snap.get("space_score", 0.5)
    per = snap.get("performance_score", 0.5)
    return round(
        w["efficiency"]*eff + w["comfort"]*com + w["safety"]*saf +
        w["reliability"]*rel + w["space"]*spa + w["performance"]*per, 4
    )

def rank_candidates(profile: UserProfile, snapshots: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    w = derive_weights(profile)
    out = []
    for s in snapshots:
        s["_score"] = score_snapshot(s, w)
        out.append(s)
    out.sort(key=lambda x: x["_score"], reverse=True)
    return out[:k]


def filter_by_condition_and_budget(cars: List[CarModel], user: UserProfile) -> Tuple[List[CarModel], List[CarModel]]:
    new_list, used_list = [], []
    if user.condition in ("new", "any"):
        new_list = [c for c in cars if c.price_new_usd and c.price_new_usd <= user.budget_usd]
    if user.condition in ("used", "any"):
        used_list = [c for c in cars if c.price_used_usd and c.price_used_usd <= user.budget_usd]
    return new_list, used_list

def rule_family_size(c: CarModel, user: UserProfile) -> float:
    if user.passengers >= 4:
        # מענישים קומפקטיות קיצונית ומתגמלים משפחתיות/קרוסאובר
        if c.seats and c.seats >= 5:
            return 0.15
        return -0.25
    return 0.0

def rule_comfort(c: CarModel, user: UserProfile) -> float:
    if user.comfort_priority and c.comfort_score is not None:
        return 0.2 * c.comfort_score
    return 0.0

def rule_fun_vs_efficiency(c: CarModel, user: UserProfile) -> float:
    if user.fun_to_drive_priority and c.handling_score is not None:
        return 0.15 * c.handling_score
    if not user.fun_to_drive_priority and c.efficiency_score is not None:
        return 0.15 * c.efficiency_score
    return 0.0

def rule_terrain(c: CarModel, user: UserProfile) -> float:
    if user.terrain == "hilly":
        # תגמול לרכבים עם מנוע חזק/הנעה מתאימה (פשטנו ל-handling_score)
        return 0.05 * (c.handling_score or 0)
    return 0.0

def rule_special_needs(c: CarModel, user: UserProfile) -> float:
    bonus = 0.0
    needs = set(user.special_needs or [])
    if "tow_hook" in needs and c.meta and c.meta.get("tow_capacity_kg", 0) > 1000:
        bonus += 0.1
    if "awd" in needs and c.meta and c.meta.get("drivetrain") == "AWD":
        bonus += 0.1
    if "high_seating" in needs and c.meta and c.meta.get("seating_height") == "high":
        bonus += 0.08
    return bonus

def score_car(c: CarModel, user: UserProfile) -> float:
    base = 0.5  # נורמליזציה קלה
    return base + sum([
        rule_family_size(c, user),
        rule_comfort(c, user),
        rule_fun_vs_efficiency(c, user),
        rule_terrain(c, user),
        rule_special_needs(c, user),
    ])

def rank_cars(cars: List[CarModel], user: UserProfile) -> List[tuple]:
    """מחזיר [(car, score)] ממויין יורד"""
    scored = [(c, round(score_car(c, user), 3)) for c in cars]
    return sorted(scored, key=lambda x: x[1], reverse=True)
