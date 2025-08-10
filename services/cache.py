# services/cache.py
import os, json, time, hashlib
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

@dataclass
class DiskCache:
    dir: str = ".cache"
    ttl_minutes: int = 60
    enabled: bool = True

    def _path(self, key: str) -> str:
        os.makedirs(self.dir, exist_ok=True)
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.dir, f"{h}.json")

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            p = self._path(key)
            if not os.path.exists(p):
                return None
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if time.time() - obj["ts"] > self.ttl_minutes * 60:
                return None
            return obj["data"]
        except Exception:
            return None

    def set(self, key: str, data: Any) -> None:
        if not self.enabled:
            return
        try:
            p = self._path(key)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "data": data}, f, ensure_ascii=False)
        except Exception:
            pass

# אופציונלי: דקורטור נוח לקאשינג פונקציות (נשמר תואם אם השתמשנו בו קודם)
def cache_result(ttl_hours: int = 24):
    def decorator(func: Callable):
        cache = DiskCache(ttl_minutes=ttl_hours * 60)
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}|args={args}|kwargs={sorted(kwargs.items())}"
            hit = cache.get(key)
            if hit is not None:
                return hit
            res = func(*args, **kwargs)
            cache.set(key, res)
            return res
        return wrapper
    return decorator
