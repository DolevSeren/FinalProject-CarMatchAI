# scripts/regression_checks.py
from __future__ import annotations
import re
from typing import Any, Dict, List
from agent.orchestrator import get_recommendations

OK = "✅"
BAD = "❌"

def _print(title: str):
    print(f"\n=== {title} ===")

def _fuel_is_bev(s: str) -> bool:
    s = (s or "").lower()
    return (
        ("bev" in s or "battery" in s or "electric" in s)
        and not any(x in s for x in ["phev", "plug-in", "hybrid", "gas", "diesel"])
    )

def _money_to_float(txt: str | None) -> float | None:
    if not txt:
        return None
    m = re.search(r"(\d[\d,]*)", str(txt))
    if not m:
        return None
    return float(m.group(1).replace(",", ""))

def assert_true(cond: bool, msg_ok: str, msg_bad: str):
    print((OK if cond else BAD), msg_ok if cond else msg_bad)
    if not cond:
        raise SystemExit(2)

def show_items(items: List[Dict[str, Any]]):
    for i, it in enumerate(items, 1):
        yr = it.get("year")
        mk, md = it.get("make"), it.get("model")
        sc = it.get("score")
        price = it.get("price_best")
        src = it.get("price_source")
        print(f"{i}. {yr} {mk} {md} | score={sc} | {price} • {src}")

def main():
    # בסיס נוח לבדיקה
    BASE = dict(
        condition="any",
        usage="mixed",
        passengers=4,
        terrain="flat",
        budget_usd=30000,
        fuel_type="any",
        top_n=3,
    )

    # 1) BEV filter — אין נזילות דלק לא מתאים
    _print("Fuel filter: BEV strictness")
    res_bev = get_recommendations({**BASE, "annual_km": 12000, "ownership_years": 3, "fuel_type": "bev"})
    print("count:", res_bev["count"])
    show_items(res_bev["results"])
    only_bev = all(_fuel_is_bev(it.get("fuelType", "")) for it in res_bev["results"])
    assert_true(only_bev, "All results are BEV-only", "Found non-BEV rows in BEV filter")

    # 2) Long ownership — סיבת אמינות מפורשת + reliability פעיל
    _print("Long ownership → reliability emphasized")
    res_long = get_recommendations({**BASE, "annual_km": 12000, "ownership_years": 6})
    print("count:", res_long["count"])
    show_items(res_long["results"])
    reason_has_long = any(
        any("Long ownership" in r or "emphasizing reliability" in r for r in (it.get("reasons") or []))
        for it in res_long["results"]
    )
    assert_true(reason_has_long, "Found explicit long-ownership reliability reason", "Missing long-ownership reliability reason")

    # 3) Low mileage — MPG de-emphasized (reason text מופיע)
    _print("Low annual km → MPG de-emphasized")
    res_low = get_recommendations({**BASE, "annual_km": 8000, "ownership_years": 3})
    print("count:", res_low["count"])
    show_items(res_low["results"])
    reason_low_miles = any(
        any("fuel economy de-prioritized" in (r or "").lower() for r in (it.get("reasons") or []))
        for it in res_low["results"]
    )
    assert_true(reason_low_miles, "Found 'fuel economy de-prioritized' reason", "Missing low-mileage de-prioritized reason")

    # 4) Budget hard filter — אף תוצאה לא מעל התקציב
    _print("Budget hard filter ≤ $22k")
    BUDGET = 22000
    res_budget = get_recommendations({**BASE, "annual_km": 12000, "ownership_years": 3, "budget_usd": BUDGET})
    print("count:", res_budget["count"])
    show_items(res_budget["results"])
    prices_ok = True
    for it in res_budget["results"]:
        p = _money_to_float(it.get("price_best"))
        if p is not None and p > BUDGET + 1e-6:
            prices_ok = False
            break
    assert_true(prices_ok, "All prices ≤ budget", "Found price above budget")

    # 5) year קיים בפלט ורואים אותו בכותרת
    _print("Result contains 'year' for UI")
    has_year = all("year" in it and it["year"] is not None for it in res_budget["results"])
    assert_true(has_year, "'year' present in all shown results", "Missing 'year' in some results")

    print("\nALL REGRESSION CHECKS PASSED ✅")

if __name__ == "__main__":
    main()