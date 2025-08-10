import os
from .http import Http
BASE = "https://marketcheck-prod.apigee.net/v2"

class Marketcheck:
    def __init__(self, http: Http | None = None, api_key: str | None = None):
        self.http = http or Http()
        self.key = api_key or os.getenv("MARKETCHECK_API_KEY")
        if not self.key:
            raise RuntimeError("MARKETCHECK_API_KEY is required")

    def search(self, query: dict) -> dict:
        params = {"api_key": self.key, **query}
        return self.http.get(f"{BASE}/search", params=params).json()