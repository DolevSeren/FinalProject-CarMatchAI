from .http import Http
BASE = "https://www.carqueryapi.com/api/0.3/"

class CarQuery:
    def __init__(self, http: Http | None = None):
        self.http = http or Http()

    def makes(self) -> list[dict]:
        r = self.http.get(BASE, params={"cmd": "getMakes", "sold_in_us": "1"})
        return r.json().get("Makes", [])

    def models(self, make: str, year: int | None = None) -> list[dict]:
        params = {"cmd": "getModels", "make": make}
        if year:
            params["year"] = year
        r = self.http.get(BASE, params=params)
        return r.json().get("Models", [])

    def trims(self, make: str, model: str, year: int | None = None) -> list[dict]:
        params = {"cmd": "getTrims", "make": make, "model": model}
        if year:
            params["year"] = year
        r = self.http.get(BASE, params=params)
        return r.json().get("Trims", [])