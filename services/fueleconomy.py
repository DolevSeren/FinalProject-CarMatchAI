from .http import Http
BASE = "https://www.fueleconomy.gov"

class FuelEconomy:
    def __init__(self, http: Http | None = None):
        self.http = http or Http()

    @staticmethod
    def _menu_items(obj: dict) -> list[dict]:
        if not isinstance(obj, dict):
            return []
        root = obj.get("menuItems") or obj
        items = root.get("menuItem") if isinstance(root, dict) else None
        return items if isinstance(items, list) else ([] if items is None else [items])

    def menu_years(self) -> list[int]:
        r = self.http.get(f"{BASE}/ws/rest/vehicle/menu/year", params={"format": "json"})
        return [int(x["text"]) for x in self._menu_items(r.json())]

    def menu_makes(self, year: int) -> list[str]:
        r = self.http.get(f"{BASE}/ws/rest/vehicle/menu/make", params={"year": year, "format": "json"})
        return [x["text"] for x in self._menu_items(r.json())]

    def menu_models(self, year: int, make: str) -> list[str]:
        r = self.http.get(f"{BASE}/ws/rest/vehicle/menu/model", params={"year": year, "make": make, "format": "json"})
        return [x["text"] for x in self._menu_items(r.json())]

    def menu_options(self, year: int, make: str, model: str) -> list[dict]:
        r = self.http.get(
            f"{BASE}/ws/rest/vehicle/menu/options",
            params={"year": year, "make": make, "model": model, "format": "json"},
        )
        return self._menu_items(r.json())

    def vehicle(self, vehicle_id: int) -> dict:
        r = self.http.get(f"{BASE}/ws/rest/vehicle/{vehicle_id}", params={"format": "json"})
        return r.json()