import json, pathlib
from typing import Tuple

class ModelNormalizer:
    def __init__(self, path="data/model_translation.json"):
        self.map = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

    def normalize(self, brand: str, model: str) -> Tuple[str, str]:
        # החזר שם "קנוני" אם יש מיפוי, אחרת השאר
        key = f"{brand} {model}".lower().strip()
        v = self.map.get(key)
        if v:
            return v.get("brand", brand), v.get("model", model)
        return brand, model
