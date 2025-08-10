from .http import Http
BASE = "https://api.nhtsa.gov"

class NhtsaRecalls:
    def __init__(self, http: Http | None = None):
        self.http = http or Http()

    def recalls(self, make: str, model: str, year: int) -> dict:
        r = self.http.get(f"{BASE}/recalls/recallsByVehicle", params={
            "make": make,
            "model": model,
            "modelYear": year,
        })
        return r.json()

    def complaints(self, make: str, model: str, year: int) -> dict:
        r = self.http.get(f"{BASE}/complaints/complaintsByVehicle", params={
            "make": make,
            "model": model,
            "modelYear": year,
        })
        return r.json()