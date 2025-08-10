# services/providers/vpic.py
"""
NHTSA VPIC – דקוד ל-VIN. במבחנים אפשר למנקי-פאץ' ולהחזיר features.
"""

from typing import Dict, Any, List
from .http import get_json


def decode_vin(vin: str) -> Dict[str, Any]:
    """
    מחזיר מילון עם לפחות מפתח "features": List[str] אם הצליח.
    """
    data = get_json("https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvaluesextended/", params={"format": "json", "vin": vin})
    features: List[str] = []

    if isinstance(data, dict):
        results = data.get("Results")
        if isinstance(results, list) and results:
            r0 = results[0]
            # ניקח כמה שדות מעניינים, אם קיימים
            for key in ("Make", "Model", "Trim", "BodyClass", "FuelTypePrimary", "DriveType"):
                val = r0.get(key)
                if isinstance(val, str) and val.strip():
                    features.append(f"{key}:{val.strip()}")

    return {"features": features} if features else {}
