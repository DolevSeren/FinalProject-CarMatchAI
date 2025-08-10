# scripts/build_catalog_us.py
import sys, os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # מאפשר import של services/*
import time, json
import pandas as pd

from services.http import Http
from services.cache import DiskCache
from services.fueleconomy import FuelEconomy
from services.nhtsa_safety import NhtsaSafety

OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True, parents=True)

YEARS = list(range(2018, 2027))  # אפשר לשנות
MAX_MAKES = None  # לשלב ניסוי: למשל 5; None = הכל

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def main():
    http = Http(user_agent="CarMatchAI-Catalog/0.1")
    cache = DiskCache(ttl_minutes=24*60)
    fe = FuelEconomy(http)
    safety = NhtsaSafety(http)

    rows = []
    for y in YEARS:
        print(f"[{y}] loading makes...")
        try:
            makes = fe.menu_makes(y)
        except Exception as e:
            print(f"  ! makes failed: {e}")
            continue
        if MAX_MAKES:
            makes = makes[:MAX_MAKES]

        for mk in makes:
            print(f"  {mk}: models...")
            try:
                models = fe.menu_models(y, mk)
            except Exception as e:
                print(f"    ! models failed: {e}")
                continue

            # טען מראש מודלי בטיחות פעם אחת ל-(year, make)
            try:
                safety_models = {_norm(m): m for m in safety.models(y, mk)}
            except Exception:
                safety_models = {}

            for mdl in models:
                try:
                    options = fe.menu_options(y, mk, mdl)
                except Exception as e:
                    print(f"    ! options {mdl} failed: {e}")
                    continue

                # ננסה להביא דירוג בטיחות פעם אחת לכל (y, mk, mdl)
                nhtsa_overall = None
                try:
                    sm = safety_models.get(_norm(mdl))
                    if sm:
                        variants = safety.variants(y, mk, sm)
                        if variants:
                            nvid = variants[0].get("VehicleId")
                            rating = safety.rating_by_vehicle_id(nvid)
                            if isinstance(rating, dict):
                                if "OverallRating" in rating:
                                    nhtsa_overall = rating.get("OverallRating")
                                else:
                                    res = rating.get("Results") or []
                                    if res:
                                        nhtsa_overall = res[0].get("OverallRating")
                except Exception:
                    pass

                for opt in options:
                    try:
                        vid = int(opt["value"])
                        veh = fe.vehicle(vid)
                    except Exception as e:
                        print(f"      ! vehicle {opt} failed: {e}")
                        continue

                    rows.append({
                        "year": y,
                        "make": mk,
                        "model": mdl,
                        "option_text": opt.get("text"),
                        "vehicle_id": vid,
                        "overall_safety": nhtsa_overall,
                        "fuelType": veh.get("fuelType") or veh.get("fuelType1"),
                        "VClass": veh.get("VClass"),
                        "MPG_comb": veh.get("comb08") or veh.get("combA08") or veh.get("combE"),
                        "Range_mi": veh.get("range") or veh.get("rangeA"),
                        "passengers": veh.get("passengers") or 5,
                        "raw_fe_json": json.dumps(veh),
                    })

                time.sleep(0.15)  # כבוד ל-API

    df = pd.DataFrame(rows)
    out_parquet = OUT_DIR / "catalog_us.parquet"
    df.to_parquet(out_parquet, index=False)
    print(f"Saved {len(df):,} rows → {out_parquet}")

if __name__ == "__main__":
    main()
