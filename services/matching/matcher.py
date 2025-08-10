from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class UserProfile:
    condition: str  # "new" | "used" | "any"
    budget: float
    passengers: int
    annual_km: int | None = None
    terrain: str | None = None  # "flat" | "hilly" | None
    years_to_keep: int | None = None
    likes: List[str] | None = None
    dislikes: List[str] | None = None
    special_needs: List[str] | None = None

@dataclass
class CarItem:
    make: str
    model: str
    price: float
    segment: str
    seats: int
    fuel: str
    is_new: bool
    meta: Dict[str, Any]


def _score_item(p: UserProfile, c: CarItem) -> float:
    score = 0.0
    # תקציב
    if c.price <= p.budget:
        score += 30.0 * (1.0 - (p.budget - c.price) / max(p.budget, 1))
    else:
        score -= 100.0

    # נוסעים
    if c.seats >= max(4, p.passengers):
        score += 15.0
    else:
        score -= 40.0

    # תנאי דרך
    if p.terrain == "hilly":
        if c.meta.get("turbo") or c.meta.get("power_kw", 0) >= 110:
            score += 8.0

    # העדפות
    text = " ".join([c.make, c.model, c.segment, c.fuel]).lower()
    for w in (p.likes or []):
        if w.lower() in text:
            score += 5.0
    for w in (p.dislikes or []):
        if w.lower() in text:
            score -= 5.0

    # אמינות (אופציונלי)
    if (p.years_to_keep or 0) >= 5 and c.meta.get("reliability_score"):
        score += c.meta["reliability_score"] * 2

    # בטיחות (אם קיים OverallRating מנורמל ל-0..5)
    if "OverallRating" in c.meta:
        try:
            score += float(c.meta["OverallRating"]) * 10
        except Exception:
            pass

    return score


def match(p: UserProfile, new_inventory: List[CarItem], used_inventory: List[CarItem], top_n: int = 5) -> List[CarItem]:
    def pick(inv: List[CarItem]):
        ranked = sorted(inv, key=lambda x: _score_item(p, x), reverse=True)
        return ranked[:top_n]

    if p.condition == "new":
        return pick([c for c in new_inventory if c.price and c.price > 0])
    if p.condition == "used":
        return pick([c for c in used_inventory if c.price and c.price > 0])

    # any → שלב כפול
    new_top = pick([c for c in new_inventory if c.price <= p.budget * 1.05])
    used_top = pick([c for c in used_inventory if c.price <= p.budget])

    out = new_top[:3]
    higher = [u for u in used_top if u.segment not in {c.segment for c in out}]
    out.extend(higher[:2])
    return out