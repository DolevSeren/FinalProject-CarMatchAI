import json, pathlib
from typing import List
from domain.user_profile import UserProfile
from domain.car import Car
from .protocols import NewCarsProvider

DATA = pathlib.Path("data/fake_new_cars.json")

class FakeNewCarsProvider(NewCarsProvider):
    def search(self, profile: UserProfile) -> List[Car]:
        items = json.loads(DATA.read_text(encoding="utf-8"))
        # פילטרים בסיסיים: תקציב, מושבים, שימוש
        out = []
        for it in items:
            if it["price"] > profile.budget:
                continue
            if it["seats"] < profile.passengers:
                continue
            out.append(Car(**it))
        return out
