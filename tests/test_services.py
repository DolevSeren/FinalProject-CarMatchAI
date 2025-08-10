import os
import pytest

from services.http import Http
from services.nhtsa_safety import NhtsaSafety
from services.nhtsa_recalls import NhtsaRecalls
from services.vpic import Vpic
from services.fueleconomy import FuelEconomy
from services.carquery import CarQuery

HTTP = Http(user_agent="CarMatchAI-Tests/0.1")
SAFETY = NhtsaSafety(HTTP)
RECALLS = NhtsaRecalls(HTTP)
VPIC = Vpic(HTTP)
FUEL = FuelEconomy(HTTP)
CQ = CarQuery(HTTP)

TEST_YEAR = 2022
TEST_MAKE = "Toyota"
TEST_MODEL = "Camry"

@pytest.mark.timeout(20)
def test_nhtsa_safety_years_and_makes_models():
    years = SAFETY.years()
    assert isinstance(years, list) and len(years) > 0
    assert any(y >= 2015 for y in years)

    makes = SAFETY.makes(TEST_YEAR)
    assert isinstance(makes, list) and len(makes) > 0
    assert TEST_MAKE in makes

    models = SAFETY.models(TEST_YEAR, TEST_MAKE)
    assert isinstance(models, list) and len(models) > 0
    assert TEST_MODEL in models

@pytest.mark.timeout(20)
def test_nhtsa_variants_and_ratings():
    variants = SAFETY.variants(TEST_YEAR, TEST_MAKE, TEST_MODEL)
    assert isinstance(variants, list) and len(variants) > 0
    vid = variants[0].get("VehicleId")
    assert isinstance(vid, int)
    rating = SAFETY.rating_by_vehicle_id(vid)
    assert isinstance(rating, dict)
    assert any(k in rating for k in ("Results", "OverallRating", "VehicleDescription"))

@pytest.mark.timeout(20)
def test_nhtsa_recalls_and_complaints():
    rec = RECALLS.recalls(TEST_MAKE, TEST_MODEL, TEST_YEAR)
    com = RECALLS.complaints(TEST_MAKE, TEST_MODEL, TEST_YEAR)
    assert isinstance(rec, dict) and isinstance(com, dict)
    assert any(k in rec for k in ("results", "Results"))
    assert any(k in com for k in ("results", "Results"))

@pytest.mark.timeout(20)
def test_vpic_makes_models_and_vin_decode_smoke():
    makes = VPIC.all_makes()
    assert isinstance(makes, list) and len(makes) > 100

    models = VPIC.models_for_make(TEST_MAKE)
    assert isinstance(models, list) and len(models) > 0

    vin = "1HGCM82633A004352"
    decoded = VPIC.decode_vin(vin)
    assert isinstance(decoded, dict)
    assert any(k in decoded for k in ("Results", "results"))

@pytest.mark.timeout(20)
def test_fueleconomy_flow_menu_to_vehicle():
    years = FUEL.menu_years()
    assert isinstance(years, list) and len(years) > 0
    assert TEST_YEAR in years or max(years) >= TEST_YEAR

    makes = FUEL.menu_makes(TEST_YEAR)
    assert isinstance(makes, list) and len(makes) > 0
    assert TEST_MAKE in makes

    models = FUEL.menu_models(TEST_YEAR, TEST_MAKE)
    assert isinstance(models, list) and len(models) > 0
    assert TEST_MODEL in models

    options = FUEL.menu_options(TEST_YEAR, TEST_MAKE, TEST_MODEL)
    assert isinstance(options, list) and len(options) > 0
    first = options[0]
    veh_id = int(first.get("value"))
    vehicle = FUEL.vehicle(veh_id)
    assert isinstance(vehicle, dict)
    assert any(k in vehicle for k in ("comb08", "combA08", "range", "phevBlended"))

@pytest.mark.timeout(20)
@pytest.mark.skipif(not os.getenv("MARKETCHECK_API_KEY"), reason="No Marketcheck key; skipping")
def test_marketcheck_search_used_camry():
    from services.marketcheck import Marketcheck
    mc = Marketcheck(HTTP)
    res = mc.search({
        "make": TEST_MAKE,
        "model": TEST_MODEL,
        "year": 2019,
        "radius": 50,
        "zip_code": 90210,
        "car_type": "used",
        "rows": 10
    })
    assert isinstance(res, dict)
    assert any(k in res for k in ("listings", "num_found", "total_listings"))