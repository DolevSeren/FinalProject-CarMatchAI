import json
import argparse
from matching.engine import load_catalog, UserProfile, rank_cars

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=str, default="data/catalog_us.parquet")
    parser.add_argument("--usage", type=str, default="mixed")
    parser.add_argument("--passengers", type=int, default=4)
    parser.add_argument("--annual_km", type=int, default=12000)
    parser.add_argument("--terrain", type=str, default="flat")
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--min_mpg", type=float, default=None)
    parser.add_argument("--max_per_model", type=int, default=1)
    parser.add_argument("--max_share_per_fuel", type=float, default=0.7)
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    profile = UserProfile(
        usage=args.usage,
        passengers=args.passengers,
        annual_km=args.annual_km,
        terrain=args.terrain,
        budget=args.budget,
    )
    df = rank_cars(
        profile,
        catalog,
        top_n=args.top,
        min_mpg=args.min_mpg,
        max_per_model=args.max_per_model,
        max_share_per_fuel=args.max_share_per_fuel,
    )
    print(df.to_json(orient="records"))
