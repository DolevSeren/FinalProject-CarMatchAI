from typing import Protocol, List, Optional
from domain.user_profile import UserProfile
from domain.car import Car

class NewCarsProvider(Protocol):
    def search(self, profile: UserProfile) -> List[Car]: ...

class UsedCarsProvider(Protocol):
    def search(self, profile: UserProfile) -> List[Car]: ...

class SpecsProvider(Protocol):
    def enrich(self, cars: List[Car]) -> List[Car]: ...
