# services/providers/vpic.py
from typing import Dict, Any, List
from . import http  # חשוב

def decode_vin(vin: str) -> Dict[str, Any]:
    data = http.get_json(
        "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvaluesextended/",
        params={"format": "json", "vin": vin}
    )
    features: List[str] = []
    if isinstance(data, dict):
        results = data.get("Results")
        if isinstance(results, list) and results:
            r0 = results[0]
            for key in ("Make", "Model", "Trim", "BodyClass", "FuelTypePrimary", "DriveType"):
                val = r0.get(key)
                if isinstance(val, str) and val.strip():
                    features.append(f"{key}:{val.strip()}")
    return {"features": features} if features else {}
