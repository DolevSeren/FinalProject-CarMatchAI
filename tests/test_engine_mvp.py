import pandas as pd
import numpy as np
from matching.engine import UserProfile, rank_cars

def _fake_row(make, model, fuel, mpg, seats=5, safety=5, vclass="Small Sport Utility Vehicle 2WD", rng=None):
    return {
        "make": make,
        "model": model,
        "option_text": "Auto (A1)",
        "VClass": vclass,
        "fuelType": fuel,
        "MPG_comb": mpg,
        "overall_safety": safety,
        "passengers": seats,
        "Range_mi": rng,
    }

def test_diversification_limits():
    # Many EVs of same model + some gas models
    rows = []
    for i in range(10):
        rows.append(_fake_row("BrandE", "E-1", "Electricity", mpg=110 + i, rng=220 + i))
    rows += [
        _fake_row("BrandG", "G-1", "Regular", mpg=30),
        _fake_row("BrandG", "G-2", "Regular", mpg=32),
        _fake_row("BrandD", "D-1", "Diesel", mpg=28),
    ]
    df = pd.DataFrame(rows)
    profile = UserProfile(passengers=4)
    out = rank_cars(profile, df, top_n=10, max_per_model=1, max_share_per_fuel=0.6)

    # no model duplicates
    assert out[["make", "model"]].duplicated().sum() == 0

    # fuel share constraint respected (<= 60% electric)
    fuel_counts = out["fuelType"].str.lower().value_counts().to_dict()
    ev = fuel_counts.get("electricity", 0)
    assert ev <= int(np.floor(0.6 * len(out)))

def test_ev_without_range_not_overrewarded():
    df = pd.DataFrame([
        _fake_row("EVCo", "ShortRange", "Electricity", mpg=115, rng=None),
        _fake_row("GasCo", "Efficient", "Regular", mpg=40),
    ])
    profile = UserProfile(passengers=4, usage="mixed")
    out = rank_cars(profile, df, top_n=2, max_per_model=1, max_share_per_fuel=0.8)
    # Both should appear; ensure EV isn't orders of magnitude ahead (sanity: score difference < 0.3)
    diff = abs(out.loc[0, "score"] - out.loc[1, "score"])
    assert diff < 0.3

def test_passenger_filter():
    df = pd.DataFrame([
        _fake_row("Mini", "TwoSeat", "Regular", mpg=40, seats=2),
        _fake_row("Family", "SixSeat", "Regular", mpg=28, seats=6),
    ])
    profile = UserProfile(passengers=5)
    out = rank_cars(profile, df, top_n=5)
    # Only the 6-seat should pass
    assert (out["model"] == "SixSeat").all()
