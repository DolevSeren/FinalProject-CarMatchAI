# services/marketcheck.py
"""
גשר תאימות:
    from services.marketcheck import MarketCheck
וגם מייצא פונקציה search מה-provider.
"""
from typing import Optional, List
from .providers.http import Http
from .providers.marketcheck import search as _search
from domain.car import Car
from domain.user_profile import UserProfile

class MarketCheck:
    def __init__(self, http: Optional[Http] = None):
        self.http = http or Http()

    def search(self, profile: UserProfile) -> List[Car]:
        return _search(profile)

# פונקציה ברמת מודול למי שמייבא כך
def search(profile: UserProfile) -> List[Car]:
    return _search(profile)
