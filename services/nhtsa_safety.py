# services/nhtsa_safety.py
from typing import Optional, List, Dict, Any
from .providers.http import Http
from .providers.nhtsa_safety import get_safety_ratings

class NhtsaSafety:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    # מתודות smoke בסיסיות – מחזירות רשימות ריקות אם אין נתונים/לא קוראים לרשת
    def years(self) -> List[int]:
        return []

    def makes(self, year: int) -> List[str]:
        return []

    def models(self, year: int, make: str) -> List[str]:
        return []

    def variants(self, year: int, make: str, model: str) -> List[str]:
        return []

    def get_ratings(self, make: str, model: str, year: int) -> Dict[str, Any]:
        return get_safety_ratings(make, model, year)

    def get(self, make: str, model: str, year: int) -> Dict[str, Any]:
        return self.get_ratings(make, model, year)
