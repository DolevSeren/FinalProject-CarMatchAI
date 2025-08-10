import json, pathlib
from domain.user_profile import UserProfile
from services.matching import matcher

def load_fixture(name):
    return json.loads(pathlib.Path(f"tests/fixtures/{name}.json").read_text(encoding="utf-8"))

def test_match_used_only(monkeypatch):
    # מחליפים קריאות רשת של כל פרוביידר להחזרת פיקסטורות
    from services.providers import http, marketcheck, carquery, fueleconomy, nhtsa_recalls, vpic

    monkeypatch.setattr(http, "get_json", lambda url, params=None, headers=None, timeout=10:
                        load_fixture("marketcheck_search"))
    monkeypatch.setattr(carquery, "get_specs", lambda brand, model, year: {"trunk_l": 430})
    monkeypatch.setattr(fueleconomy, "get_mpg", lambda brand, model, year: 45)
    monkeypatch.setattr(nhtsa_recalls, "get_recalls", lambda brand, model, year: [])
    monkeypatch.setattr(vpic, "decode_vin", lambda vin: {"features": ["VIN_OK"]})

    profile = UserProfile(
        new_or_used="used", usage="mixed", passengers=4, annual_km=12000,
        terrain="flat", budget=150000, must_haves=["efficiency"]
    )
    results = matcher.match(profile, limit=5)
    assert results, "Expected results"
    assert results[0].price <= profile.budget
