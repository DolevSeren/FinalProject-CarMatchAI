import time, random
import requests

DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3

class Http:
    def __init__(self, user_agent: str = "CarMatchAI/0.1"):
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })

    def get(self, url: str, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = self.sess.get(url, params=params, timeout=timeout)
                if r.status_code >= 500:
                    raise requests.RequestException(f"{r.status_code}")
                return r
            except requests.RequestException:
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(0.4 * attempt + random.random() * 0.2)