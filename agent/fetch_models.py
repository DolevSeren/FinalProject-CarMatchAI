# agent/fetch_models.py
import json
import os
from typing import List, Dict

def fetch_models(year_from: int = 2019, limit: int = 50) -> List[Dict]:
    """Load car models from local JSON file (mock data for MVP)."""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models_sample.json")
    with open(data_file, "r", encoding="utf-8") as f:
        models = json.load(f)

    # סינון לפי שנה ומגבלת כמות
    filtered = [m for m in models if m["year"] >= year_from]
    return filtered[:limit]
