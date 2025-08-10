# services/nhtsa_recalls.py
from typing import Optional, List, Dict, Any
from .providers.http import Http
from .providers.nhtsa_recalls import get_recalls as _get_recalls

class NhtsaRecalls:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    def get(self, make: str, model: str, year: int) -> List[Dict[str, Any]]:
        return _get_recalls(make, model, year)

    # שם שהמבחן מחפש:
    def recalls(self, make: str, model: str, year: int) -> List[Dict[str, Any]]:
        return self.get(make, model, year)
