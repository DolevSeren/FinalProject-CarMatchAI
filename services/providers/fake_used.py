import json, pathlib
from typing import List
from domain.user_profile import UserProfile
from domain.car import Car
from .protocols import UsedCarsProvider

DATA = pathlib.Path("data/fake_used_cars.json")

class FakeUsedCarsProvider(UsedCarsProvider):
    def search(self, profile: UserProfile) -> List[Car]:
        items = json.loads(DATA.read_text(encoding="utf-8"))
        out = []
        for it in items:
            if it["price"] > profile.budget:
                continue
            if it["seats"] < profile.passengers:
                continue
            out.append(Car(**it))
        return out
