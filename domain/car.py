from dataclasses import dataclass
from typing import Optional, List, Literal

@dataclass
class Car:
    id: str
    brand: str
    model: str
    year: int
    price: int
    powertrain: Literal["gas", "diesel", "hybrid", "phev", "ev"]
    body: str  # hatch, sedan, suv, wagon...
    seats: int
    trunk_l: Optional[int]
    comfort_score: Optional[float]  # 0-10 (אפשר לאמוד/להביא ממקור טכני)
    efficiency_score: Optional[float]  # 0-10
    driving_fun_score: Optional[float]  # 0-10
    source: Literal["importer", "yad2", "specs"]
    url: Optional[str] = None
    features: Optional[List[str]] = None
