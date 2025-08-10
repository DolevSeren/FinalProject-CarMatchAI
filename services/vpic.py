# services/vpic.py
from typing import Optional, Dict, Any, List
from .providers.http import Http
from .providers.vpic import decode_vin as _decode_vin

class Vpic:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    def decode_vin(self, vin: str) -> Dict[str, Any]:
        return _decode_vin(vin)

    def decode(self, vin: str) -> Dict[str, Any]:
        return self.decode_vin(vin)

    # smoke helpers (לא קוראים לרשת)
    def all_makes(self) -> List[str]:
        return []

    def all_models(self, make: str, year: int | None = None) -> List[str]:
        return []
