# agent/enrich_model.py
from typing import Dict, Any

MOCK_DB = {
    ("Toyota","Corolla"): {
        "msrp_usd": 23000, "used_median": 18500,
        "equipment": ["ADAS basics","CarPlay","LED headlights"],
        "comfort_score": 0.65, "materials_note":"mid-pack",
        "safety_score": 0.86, "reliability_score": 0.90, "efficiency_score": 0.78,
        "space_score": 0.40, "performance_score": 0.45,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Honda","Civic"): {
        "msrp_usd": 25000, "used_median": 21000,
        "equipment": ["ADAS","CarPlay/AA","Adaptive cruise"],
        "comfort_score": 0.68, "materials_note":"solid",
        "safety_score": 0.88, "reliability_score": 0.85, "efficiency_score": 0.74,
        "space_score": 0.48, "performance_score": 0.55,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Toyota","RAV4"): {
        "msrp_usd": 29500, "used_median": 27000,
        "equipment": ["AWD opt","Power liftgate","CarPlay"],
        "comfort_score": 0.72, "materials_note":"good",
        "safety_score": 0.90, "reliability_score": 0.88, "efficiency_score": 0.75,
        "space_score": 0.80, "performance_score": 0.60,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Kia","Sportage"): {
        "msrp_usd": 28500, "used_median": 25500,
        "equipment": ["Wide screen","ADAS","CarPlay/AA"],
        "comfort_score": 0.73, "materials_note":"improved",
        "safety_score": 0.89, "reliability_score": 0.84, "efficiency_score": 0.76,
        "space_score": 0.78, "performance_score": 0.58,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Tesla","Model 3"): {
        "msrp_usd": 38500, "used_median": 31000,
        "equipment": ["EV","OTA updates","ADAS"],
        "comfort_score": 0.78, "materials_note":"minimalist",
        "safety_score": 0.93, "reliability_score": 0.70, "efficiency_score": 0.95,
        "space_score": 0.65, "performance_score": 0.85,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Subaru","Outback"): {
        "msrp_usd": 30000, "used_median": 26000,
        "equipment": ["Standard AWD","Roof rails","EyeSight"],
        "comfort_score": 0.76, "materials_note":"robust",
        "safety_score": 0.92, "reliability_score": 0.80, "efficiency_score": 0.69,
        "space_score": 0.75, "performance_score": 0.55,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Honda","CR-V"): {
        "msrp_usd": 30000, "used_median": 27000,
        "equipment": ["Spacious","ADAS","AWD opt"],
        "comfort_score": 0.74, "materials_note":"nice",
        "safety_score": 0.91, "reliability_score": 0.86, "efficiency_score": 0.75,
        "space_score": 0.80, "performance_score": 0.60,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    },
    ("Toyota","Sienna"): {
        "msrp_usd": 37000, "used_median": 33500,
        "equipment": ["7 seats","Hybrid","AWD"],
        "comfort_score": 0.82, "materials_note":"family-focused",
        "safety_score": 0.90, "reliability_score": 0.88, "efficiency_score": 0.80,
        "space_score": 0.90, "performance_score": 0.55,
        "sources": {"price_new":"https://manufacturer.example","review":"https://review.example"}
    }
}

def enrich_model(make: str, model: str, year: int, body: str) -> dict[str, Any]:
    """דמו: מחזיר צילום מצב לדגם כולל ציונים/מחירים בסיסיים"""
    base = {
        "make": make, "model": model, "year": year, "body": body,
        "sources": {}
    }
    d = MOCK_DB.get((make, model))
    if not d:
        # דיפולט אם אין בדמו
        return {**base,
            "msrp_usd": None, "used_median": None, "equipment": [],
            "comfort_score": 0.5, "materials_note":"unknown",
            "safety_score": 0.5, "reliability_score": 0.5, "efficiency_score": 0.5,
            "space_score": 0.5, "performance_score": 0.5,
            "sources": {}
        }
    return {**base, **d}
