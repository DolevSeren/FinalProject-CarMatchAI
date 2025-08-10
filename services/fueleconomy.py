# services/fueleconomy.py
from typing import Optional, List, Dict, Any
from .providers.http import Http
from .providers.fueleconomy import get_mpg as _get_mpg

class FuelEconomy:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    def get_mpg(self, brand: str, model: str, year: int):
        return _get_mpg(brand, model, year)

    # smoke helpers (לא קוראים לרשת)
    def menu_years(self) -> List[int]:
        return []

    def menu_makes(self, year: int) -> List[str]:
        return []

    def menu_models(self, year: int, make: str) -> List[str]:
        return []

    def menu_options(self, year: int, make: str, model: str) -> List[Dict[str, Any]]:
        return []
