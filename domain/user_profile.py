from dataclasses import dataclass
from typing import Literal, Optional, List

UsageType = Literal["urban", "intercity", "mixed"]

@dataclass
class UserProfile:
    new_or_used: Literal["new", "used", "any"]
    usage: UsageType
    passengers: int
    annual_km: Optional[int]
    terrain: Literal["flat", "hilly", "mixed"]
    budget: int
    current_car: Optional[str] = None
    liked: Optional[List[str]] = None
    disliked: Optional[List[str]] = None
    must_haves: Optional[List[str]] = None
    years_to_keep: Optional[int] = None
    special_needs: Optional[List[str]] = None
