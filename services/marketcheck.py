# services/marketcheck.py
import os, json
from pathlib import Path
from .http import Http
from .cache import DiskCache

BASE = "https://marketcheck-prod.apigee.net/v2"
MODE = os.getenv("MARKETCHECK_MODE", "mock").lower()  # "mock" | "live"
MOCK_DIR = Path("mock_data"); MOCK_DIR.mkdir(exist_ok=True)

class Marketcheck:
    def __init__(self, http: Http | None = None, api_key: str | None = None, cache: DiskCache | None = None):
        self.http = http or Http()
        self.key = api_key or os.getenv("MARKETCHECK_API_KEY")
        self.cache = cache or DiskCache(ttl_minutes=24*60)

    def _cache_key(self, **q): return "mc:" + "|".join(f"{k}={q[k]}" for k in sorted(q.keys()))

    def search_used(self, make: str, model: str, year: int | None = None, zip_code: int | None = None,
                    radius: int = 50, rows: int = 50) -> dict:
        query = {"make": make, "model": model, "car_type": "used", "radius": radius, "rows": rows}
        if year: query["year"] = year
        if zip_code: query["zip_code"] = zip_code

        if MODE == "mock":
            # קובץ mock לפי שם
            name = f"marketcheck_{make}_{model}_{year or 'any'}_{zip_code or 'NA'}_{radius}.json".replace(" ", "_")
            p = MOCK_DIR / name
            if p.exists():
                return json.loads(p.read_text())
            # אין קובץ? נחזיר מבנה ריק סביר
            return {"listings": []}

        # LIVE
        if not self.key:
            raise RuntimeError("MARKETCHECK_API_KEY is required for live mode")

        ck = self._cache_key(**query)
        cached = self.cache.get(ck)
        if cached: return cached

        params = {"api_key": self.key, **query}
        res = self.http.get(f"{BASE}/search", params=params).json()
        self.cache.set(ck, res)

        # שומר גם קובץ mock לשימוש עתידי
        name = f"marketcheck_{make}_{model}_{year or 'any'}_{zip_code or 'NA'}_{radius}.json".replace(" ", "_")
        (MOCK_DIR / name).write_text(json.dumps(res, ensure_ascii=False, indent=2))
        return res

    @staticmethod
    def summarize_listings(res: dict) -> dict:
        listings = (res or {}).get("listings") or []
        prices = [float(x.get("price")) for x in listings if x.get("price")]
        prices.sort()
        if not prices: return {"count": len(listings), "sample": listings[:10]}
        n = len(prices); med = prices[n//2] if n % 2 else (prices[n//2-1]+prices[n//2])/2
        return {
            "count": len(listings),
            "min": min(prices),
            "median": med,
            "avg": sum(prices)/n,
            "max": max(prices),
            "sample": [
                {
                    "year": (x.get("build") or {}).get("year"),
                    "make": (x.get("build") or {}).get("make"),
                    "model": (x.get("build") or {}).get("model"),
                    "trim": (x.get("build") or {}).get("trim"),
                    "miles": x.get("miles"),
                    "price": x.get("price"),
                    "dealer_city": (x.get("dealer") or {}).get("city"),
                    "dealer_state": (x.get("dealer") or {}).get("state"),
                    "vdp_url": x.get("vdp_url"),
                } for x in listings[:10]
            ],
        }
