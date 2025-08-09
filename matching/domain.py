from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass
class CarModel:
    make: str
    model: str
    year_from: int
    year_to: Optional[int]
    body_style: Optional[str]
    powertrain: Optional[str]  # ICE / HEV / PHEV / BEV
    seats: Optional[int]
    cargo_l: Optional[int]
    comfort_score: Optional[float]  # 0-1
    handling_score: Optional[float] # 0-1
    efficiency_score: Optional[float] # 0-1
    price_new_usd: Optional[float]
    price_used_usd: Optional[float]  # מחיר ממוצע/חציוני
    meta: Dict[str, Any] = None

@dataclass
class UserProfile:
    condition: str  # "new" / "used" / "any"
    budget_usd: float
    passengers: int
    annual_km: Optional[int]
    terrain: Optional[str]  # "flat" / "hilly" / None
    comfort_priority: bool
    fun_to_drive_priority: bool
    years_to_keep: Optional[int]
    special_needs: List[str]  # ["tow_hook","awd","high_seating",...]
