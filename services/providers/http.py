# services/providers/http.py
import time
import requests
from typing import Optional, Dict, Any

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_UA = "CarMatchAI/1.0"


class ProviderError(RuntimeError):
    """שגיאה כללית לשכבת הפרוביידרים (HTTP/API)."""
    pass


class Http:
    """
    עטיפת HTTP עם retries/backoff, כותרת User-Agent, וטיים-אאוט.
    תואם למבחנים שמבצעים: Http(user_agent="...").get_json(...)
    """
    def __init__(self, user_agent: str = DEFAULT_UA, timeout: int = DEFAULT_TIMEOUT, max_retries: int = DEFAULT_MAX_RETRIES):
        self.user_agent = user_agent or DEFAULT_UA
        self.timeout = timeout
        self.max_retries = max_retries

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
        ua_headers = {"User-Agent": self.user_agent}
        if headers:
            ua_headers.update(headers)

        use_timeout = timeout if timeout is not None else self.timeout
        last_exc = None

        for attempt in range(1, (self.max_retries or 1) + 1):
            try:
                r = requests.get(url, params=params, headers=ua_headers, timeout=use_timeout)
                if r.status_code >= 400:
                    raise ProviderError(f"{url} -> HTTP {r.status_code}: {r.text[:200]}")
                return r.json()
            except (requests.RequestException, ValueError) as e:
                last_exc = e
                if attempt < (self.max_retries or 1):
                    # backoff לינארי פשוט: 0.6s, 1.2s, 1.8s...
                    time.sleep(0.6 * attempt)
                else:
                    raise ProviderError(f"Failed {url}: {e}") from e


# מופע ברירת מחדל לפונקציה ברמת מודול
_default_http = Http()


def get_json(url: str, params: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
    """
    פונקציה נוחה לשימוש מהיר: services.providers.http.get_json(...)
    משתמשת במופע ברירת המחדל Http().
    """
    return _default_http.get_json(url, params=params, headers=headers, timeout=timeout)
