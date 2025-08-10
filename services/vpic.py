from .http import Http
BASE = "https://vpic.nhtsa.dot.gov/api/vehicles"

class Vpic:
    def __init__(self, http: Http | None = None):
        self.http = http or Http()

    def all_makes(self) -> list[dict]:
        return self.http.get(f"{BASE}/getallmakes?format=json").json().get("Results", [])

    def models_for_make(self, make: str) -> list[dict]:
        return self.http.get(f"{BASE}/GetModelsForMake/{make}?format=json").json().get("Results", [])

    def decode_vin(self, vin: str, year: int | None = None) -> dict:
        url = f"{BASE}/DecodeVINValues/{vin}?format=json"
        if year:
            url += f"&modelyear={year}"
        return self.http.get(url).json()