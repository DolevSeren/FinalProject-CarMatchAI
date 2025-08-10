# matching/engine.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import os


# ---------------- Data model ----------------
@dataclass
class UserProfile:
    new_or_used: str = "any"
    usage: str = "mixed"                   # "city" / "highway" / "mixed"
    passengers: int = 4
    annual_km: int = 12000
    terrain: str = "flat"                  # "flat" / "hilly"
    budget: Optional[float] = None         # USD; used only if price present

    prioritize_mpg: bool = True
    prioritize_safety: bool = True
    prioritize_space: bool = False

    # Optional manual weights override
    weights: Dict[str, float] = field(default_factory=dict)


# ---------------- Heuristics & helpers ----------------
VCLASS_SIZE_RULES = [
    ("Two Seaters", 0.10),
    ("Minicompact", 0.15),
    ("Subcompact", 0.25),
    ("Compact", 0.35),
    ("Midsize", 0.55),
    ("Large", 0.75),
    ("Small SUV", 0.45),
    ("Midsize SUV", 0.65),
    ("Large SUV", 0.85),
    ("Minivan", 0.80),
    ("Wagon", 0.50),
    ("Pickup", 0.90),
    ("Van", 0.85),
]

def _vclass_size_score(vclass: str) -> float:
    if not isinstance(vclass, str) or not vclass:
        return 0.55
    vc = vclass.lower()
    for key, score in VCLASS_SIZE_RULES:
        if key.lower() in vc:
            return float(score)
    if "suv" in vc:
        return 0.65
    if "truck" in vc or "pickup" in vc:
        return 0.90
    if "car" in vc:
        if "compact" in vc:
            return 0.35
        if "midsize" in vc:
            return 0.55
        if "large" in vc:
            return 0.75
        return 0.55
    return 0.55


def _robust_minmax(x: pd.Series, low_q: float = 0.05, high_q: float = 0.95) -> pd.Series:
    x = pd.to_numeric(x, errors="coerce").astype(float)
    lo = x.quantile(low_q)
    hi = x.quantile(high_q)
    rng = max(hi - lo, 1e-9)
    scaled = (x - lo) / rng
    return scaled.clip(0.0, 1.0)


def _safety_to_numeric(s: Any) -> float:
    if s is None:
        return 0.5
    try:
        val = float(s)
        if np.isnan(val):
            return 0.5
        return float(np.clip(val / 5.0, 0.0, 1.0))
    except Exception:
        return 0.5


def _usage_fit(vclass_size: float, usage: str) -> float:
    u = (usage or "mixed").lower()
    if u == "city":
        return float(1.0 - vclass_size)
    if u == "highway":
        return float(vclass_size)
    return float(1.0 - abs(vclass_size - 0.6))


def _passenger_fit(capacity: Any, required: int) -> float:
    try:
        cap = int(capacity)
    except Exception:
        return 0.0
    if cap >= required:
        return float(min(1.0, 0.8 + 0.2 * (cap / max(required, 1))))
    return float(max(0.0, cap / max(required, 1)))


def _budget_fit(price: Optional[float], budget: Optional[float]) -> float:
    if price is None or budget is None:
        return 0.5
    try:
        price = float(price)
        budget = float(budget)
    except Exception:
        return 0.5
    if price <= budget:
        ratio = price / max(budget, 1.0)
        return float(np.clip(1.0 - 0.6 * (1.0 - ratio), 0.0, 1.0))
    over = (price - budget) / max(budget, 1.0)
    return float(np.clip(0.7 - 1.5 * over, 0.0, 0.7))


DEFAULT_WEIGHTS = {
    "mpg": 0.40,
    "safety": 0.30,
    "passengers": 0.20,
    "usage": 0.10,
}


# ---------------- Catalog IO ----------------
def load_catalog(path: str | None = None) -> pd.DataFrame:
    path = path or os.getenv("CARMATCH_US_CATALOG", "data/catalog_us.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Catalog not found: {path}")
    df = pd.read_parquet(path)
    return df


def preprocess_catalog(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    expected = [
        "make", "model", "option_text", "VClass", "MPG_comb", "overall_safety",
        "passengers", "fuelType", "Range_mi", "electricRange_mi"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = np.nan

    df["vclass_size"] = df["VClass"].map(_vclass_size_score)

    # MPG normalization per fuel type to avoid EVs dominating
    fuel_key = df["fuelType"].fillna("unknown").astype(str)
    df["mpg_norm"] = df.groupby(fuel_key)["MPG_comb"].transform(lambda s: _robust_minmax(s))

    df["safety_norm"] = df["overall_safety"].apply(_safety_to_numeric)

    return df


# ---------------- Scoring ----------------
def _effective_weights(profile: UserProfile, df: pd.DataFrame) -> Dict[str, float]:
    w = DEFAULT_WEIGHTS.copy()
    if profile.prioritize_mpg:
        w["mpg"] += 0.05
    if profile.prioritize_safety:
        w["safety"] += 0.05
    if profile.prioritize_space:
        w["passengers"] += 0.05

    has_price = any(col in df.columns for col in ("msrp", "price"))
    if has_price and profile.budget:
        w["budget"] = 0.15
        non_budget_sum = sum(v for k, v in w.items() if k != "budget")
        for k in list(w.keys()):
            if k != "budget":
                w[k] *= (1.0 - w["budget"]) / max(non_budget_sum, 1e-9)

    for k, v in (profile.weights or {}).items():
        w[k] = float(v)

    total = sum(w.values())
    for k in list(w.keys()):
        w[k] = w[k] / max(total, 1e-9)
    return w


def score_vehicle_row_v2(row: pd.Series, profile: UserProfile, weights: Dict[str, float]) -> Dict[str, Any]:
    reasons: List[str] = []

    # Seating
    p_fit = _passenger_fit(row.get("passengers"), profile.passengers)
    if p_fit >= 1.0:
        reasons.append(f"Seats {int(row.get('passengers', 0))} ≥ required {profile.passengers}")
    elif p_fit >= 0.8:
        reasons.append(f"Seating OK ({int(row.get('passengers', 0))})")
    else:
        reasons.append(f"May be tight: seats {int(row.get('passengers') or 0)} vs {profile.passengers}")

    # Efficiency with EV/PHEV range nuance
    mpg = row.get("MPG_comb")
    try:
        mpg_int = int(mpg) if pd.notna(mpg) else None
    except Exception:
        mpg_int = None
    mpg_norm = float(row.get("mpg_norm") or 0.0)
    eff_norm = mpg_norm
    fuel = (row.get("fuelType") or "").lower()

    def _fit_from_range(rng, min_ref, max_ref):
        try:
            r = float(rng)
        except Exception:
            return None
        if np.isnan(r):
            return None
        return float(np.clip((r - min_ref) / max(1e-9, (max_ref - min_ref)), 0.0, 1.0))

    if "electric" in fuel and "gas" not in fuel:
        # BEV: use Range_mi (typical EPA range)
        range_fit = _fit_from_range(row.get("Range_mi"), 150.0, 300.0)
        if range_fit is not None:
            eff_norm = 0.7 * mpg_norm + 0.3 * range_fit
            try:
                reasons.append(f"EV range {int(float(row.get('Range_mi')))} mi (range fit {range_fit:.2f})")
            except Exception:
                reasons.append(f"EV range fit {range_fit:.2f}")
    elif "gas" in fuel and "electric" in fuel:
        # PHEV: use electricRange_mi if provided (electric-only range)
        elec = row.get("electricRange_mi")
        range_fit = _fit_from_range(elec, 20.0, 60.0)
        if range_fit is not None:
            eff_norm = 0.85 * mpg_norm + 0.15 * range_fit
            try:
                reasons.append(f"PHEV electric range {int(float(elec))} mi (range fit {range_fit:.2f})")
            except Exception:
                reasons.append(f"PHEV electric range fit {range_fit:.2f}")

    if mpg_int is not None:
        reasons.append(f"Combined MPG/MPGe {mpg_int} (efficiency score {eff_norm:.2f})")

    # Safety
    saf_norm = float(row.get("safety_norm") or 0.0)
    saf_raw = row.get("overall_safety")
    if pd.notna(saf_raw):
        reasons.append(f"NHTSA overall {saf_raw}")
    else:
        reasons.append("Safety not rated — treated neutral")

    # Usage fit (size vs usage)
    size = float(row.get("vclass_size") or 0.55)
    u_fit = _usage_fit(size, profile.usage)
    reasons.append(f"Usage fit {u_fit:.2f} for {profile.usage}")

    # Budget
    price = None
    for c in ("msrp", "price"):
        if c in row and pd.notna(row[c]):
            try:
                price = float(row[c])
                break
            except Exception:
                pass
    b_fit = _budget_fit(price, profile.budget)
    if price is not None and profile.budget is not None:
        reasons.append(f"Budget fit {b_fit:.2f} (price {price:,.0f} vs budget {profile.budget:,.0f})")

    score = (
        weights.get("passengers", 0.0) * p_fit
        + weights.get("mpg", 0.0) * eff_norm
        + weights.get("safety", 0.0) * saf_norm
        + weights.get("usage", 0.0) * u_fit
        + weights.get("budget", 0.0) * b_fit
    )

    return {"score": float(score), "reasons": reasons}


# ---------------- Post-processing ----------------
def _dedupe_rows(df: pd.DataFrame) -> pd.DataFrame:
    keys = [c for c in ["make", "model", "option_text", "VClass", "fuelType", "MPG_comb", "overall_safety", "passengers"] if c in df.columns]
    return df.drop_duplicates(subset=keys)


def _diversify(
    df_sorted: pd.DataFrame,
    top_n: int,
    max_per_model: int = 1,
    max_share_per_fuel: float = 0.7,
) -> pd.DataFrame:
    """Greedy re-ranker to enforce diversity by model and fuel type."""
    selected_idx: list[int] = []
    model_counts: Dict[tuple[str, str], int] = {}
    fuel_counts: Dict[str, int] = {}

    def can_take(row: pd.Series) -> bool:
        mk = str(row.get("make", "")).strip()
        md = str(row.get("model", "")).strip()
        key = (mk, md)
        model_ok = model_counts.get(key, 0) < max_per_model

        fuel = str(row.get("fuelType", "unknown")).strip().lower() or "unknown"
        current_total = len(selected_idx)
        fuel_ok = True
        if current_total + 1 > 0:
            projected = fuel_counts.get(fuel, 0) + 1
            fuel_ok = (projected / (current_total + 1)) <= max_share_per_fuel

        return model_ok and fuel_ok

    # First pass: enforce both limits
    for idx, row in df_sorted.iterrows():
        if len(selected_idx) >= top_n:
            break
        if can_take(row):
            selected_idx.append(idx)
            mk = str(row.get("make", "")).strip()
            md = str(row.get("model", "")).strip()
            model_counts[(mk, md)] = model_counts.get((mk, md), 0) + 1
            fuel = str(row.get("fuelType", "unknown")).strip().lower() or "unknown"
            fuel_counts[fuel] = fuel_counts.get(fuel, 0) + 1

    # Second pass: relax fuel limit if needed, keep model limit
    if len(selected_idx) < top_n:
        for idx, row in df_sorted.iterrows():
            if len(selected_idx) >= top_n:
                break
            if idx in selected_idx:
                continue
            mk = str(row.get("make", "")).strip()
            md = str(row.get("model", "")).strip()
            key = (mk, md)
            if model_counts.get(key, 0) < max_per_model:
                selected_idx.append(idx)
                model_counts[key] = model_counts.get(key, 0) + 1

    if not selected_idx:
        return df_sorted.head(top_n).reset_index(drop=True)
    return df_sorted.loc[selected_idx].reset_index(drop=True)


# ---------------- Public API ----------------
def rank_cars(
    profile: UserProfile,
    catalog: pd.DataFrame,
    top_n: int = 20,
    min_mpg: Optional[float] = None,
    max_per_model: int = 1,
    max_share_per_fuel: float = 0.7,
    fuel_type: Optional[str] = None,   # optional extra filter ("gas"/"bev"/"phev"/"any")
) -> pd.DataFrame:
    df = preprocess_catalog(catalog)

    # Hard filters
    df = df[df["passengers"].fillna(0) >= max(1, int(profile.passengers or 1))]
    if min_mpg is not None and "MPG_comb" in df.columns:
        df = df[pd.to_numeric(df["MPG_comb"], errors="coerce").fillna(0) >= float(min_mpg)]

    # Optional fuel filter here as a safety (or when using directly)
    if fuel_type:
        ft = (str(fuel_type) or "").strip().lower()
        s = df["fuelType"].astype(str)
        if ft and ft != "any":
            if ft == "bev":
                df = df[s.str.contains("Electric", case=False, na=False) & ~s.str.contains("Gas", case=False, na=False)]
            elif ft == "phev":
                df = df[s.str.contains("Gas", case=False, na=False) & s.str.contains("Electric", case=False, na=False)]
            elif ft == "gas":
                df = df[~s.str.contains("Electric", case=False, na=False)]

    df = _dedupe_rows(df)
    if df.empty:
        return df

    weights = _effective_weights(profile, df)

    scored: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        res = score_vehicle_row_v2(row, profile, weights)
        scored.append(res)

    out = df.copy()
    out["score"] = [s["score"] for s in scored]
    out["reasons"] = [s["reasons"] for s in scored]

    keep = [
        "make", "model", "option_text", "VClass", "fuelType",
        "passengers", "MPG_comb", "overall_safety", "Range_mi", "electricRange_mi", "score", "reasons",
    ]
    existing_keep = [c for c in keep if c in out.columns]
    out = out[existing_keep].sort_values(["score", "overall_safety", "MPG_comb"], ascending=[False, False, False])

    # Diversify
    out = _diversify(out, top_n=top_n, max_per_model=max_per_model, max_share_per_fuel=max_share_per_fuel)
    return out


# ---------------- CLI ----------------
if __name__ == "__main__":
    import argparse
    pd.set_option("display.max_colwidth", 120)

    parser = argparse.ArgumentParser(description="CarMatch AI — rank cars for a profile")
    parser.add_argument("--catalog", type=str, default=os.getenv("CARMATCH_US_CATALOG", "data/catalog_us.parquet"))
    parser.add_argument("--usage", type=str, default="mixed", choices=["city", "highway", "mixed"])
    parser.add_argument("--passengers", type=int, default=4)
    parser.add_argument("--annual_km", type=int, default=12000)
    parser.add_argument("--terrain", type=str, default="flat", choices=["flat", "hilly"])
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--fuel_type", type=str, default="any", choices=["any", "gas", "phev", "bev"])
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--min_mpg", type=float, default=None)
    parser.add_argument("--max_per_model", type=int, default=1)
    parser.add_argument("--max_share_per_fuel", type=float, default=0.7)
    args = parser.parse_args()

    print("\nLoading catalog…", args.catalog)
    catalog = load_catalog(args.catalog)

    profile = UserProfile(
        usage=args.usage,
        passengers=args.passengers,
        annual_km=args.annual_km,
        terrain=args.terrain,
        budget=args.budget,
    )

    ranked = rank_cars(
        profile,
        catalog,
        top_n=args.top,
        min_mpg=args.min_mpg,
        max_per_model=args.max_per_model,
        max_share_per_fuel=args.max_share_per_fuel,
        fuel_type=args.fuel_type,
    )

    if ranked.empty:
        print("No vehicles matched your filters. Try relaxing constraints.")
    else:
        cols = [c for c in ["make", "model", "option_text", "VClass", "fuelType", "passengers", "MPG_comb", "overall_safety", "Range_mi", "electricRange_mi", "score"] if c in ranked.columns]
        print("\nTop results:\n")
        print(ranked[cols].to_string(index=False, formatters={"score": "{:.3f}".format}))
        print("\nReasons (per row):\n")
        for i, reasons in enumerate(ranked.get("reasons", [])):
            print(f"#{i+1}")
            for r in reasons:
                print("  -", r)
            print()
