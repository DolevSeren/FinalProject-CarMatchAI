from .http import Http
BASE = "https://api.nhtsa.gov"

class NhtsaSafety:
    def __init__(self, http: Http | None = None):
        self.http = http or Http()

    def years(self) -> list[int]:
        r = self.http.get(f"{BASE}/SafetyRatings")
        return sorted({int(x["ModelYear"]) for x in r.json().get("Results", []) if x.get("ModelYear")})

    def makes(self, year: int) -> list[str]:
        r = self.http.get(f"{BASE}/SafetyRatings/modelyear/{year}")
        makes = {x.get("Make", "").strip() for x in r.json().get("Results", [])}
        return sorted(m.title() for m in makes if m)

    def models(self, year: int, make: str) -> list[str]:
        r = self.http.get(f"{BASE}/SafetyRatings/modelyear/{year}/make/{make}")
        models = {x.get("Model", "").strip() for x in r.json().get("Results", [])}
        return sorted(m.title() for m in models if m)

    def variants(self, year: int, make: str, model: str) -> list[dict]:
        r = self.http.get(f"{BASE}/SafetyRatings/modelyear/{year}/make/{make}/model/{model}")
        return r.json().get("Results", [])

    def rating_by_vehicle_id(self, vehicle_id: int) -> dict:
        r = self.http.get(f"{BASE}/SafetyRatings/VehicleId/{vehicle_id}")
        return r.json()