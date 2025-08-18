# scripts/smoke_recommendations.py
from __future__ import annotations
import sys
from typing import Dict, Any, List

# מאפשר הרצה גם אם מכוונים מהשורש של הפרויקט
try:
    from agent.orchestrator import get_recommendations
except Exception as e:
    print("Import error:", e)
    print("Make sure you run this from the repo root, e.g.:")
    print("  python -m scripts.smoke_recommendations")
    sys.exit(1)

TOP_N = 3

def simple_recap(a: Dict[str, Any]) -> str:
    parts: List[str] = []
    if a.get("condition") and a["condition"] != "any":
        parts.append(f"You’re open to {a['condition']} cars.")
    if a.get("budget_usd"):
        parts.append(f"Budget is about ${int(a['budget_usd']):,}.")
    if a.get("fuel_type") and a["fuel_type"] != "any":
        parts.append(f"Fuel preference: {a['fuel_type']}.")
    if a.get("passengers"):
        p = int(a["passengers"])
        if p <= 2:
            parts.append("You usually drive solo or with one passenger, so space isn’t critical.")
        elif p >= 5:
            parts.append("You often have 5+ passengers, so we’ll focus on roomier options.")
        else:
            parts.append(f"Typically {p} passengers.")
    km = a.get("annual_km")
    if km:
        if km < 10000:
            parts.append("You drive relatively little each year, so fuel economy matters less.")
        else:
            parts.append(f"You drive ~{km:,} km/year, so efficiency can save you money.")
    yrs = a.get("ownership_years")
    if yrs:
        if yrs >= 5:
            parts.append(f"You plan to keep the car ~{yrs} years, so reliability will be emphasized.")
        else:
            parts.append(f"Planned ownership is ~{yrs} years.")
    return " ".join(parts) or "Got it. I’ll tailor recommendations to your answers."

def show_case(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")

    # אמולציה של כללי ה־UI: אם annual_km < 10k — נכבה MPG
    skip_mpg = False
    if (payload.get("annual_km") or 0) and payload["annual_km"] < 10000:
        # רק אם המשתמש לא הכריע במפורש אחרת
        if "prioritize_mpg" not in payload:
            payload["prioritize_mpg"] = False
        skip_mpg = not payload["prioritize_mpg"]

    # תמיד מבקשים TOP_N=3 כמו ב־App
    payload = {**payload, "top_n": TOP_N}

    # Recap פשוט לפני ההרצה
    print("Recap:", simple_recap(payload))
    if skip_mpg:
        print("Note: annual_km < 10k → MPG de-emphasized.")

    res = get_recommendations(payload)
    items = res.get("results", [])[:TOP_N]
    print("count:", len(items))

    if not items:
        print("No vehicles matched your filters.")
        return

    for i, it in enumerate(items, 1):
        year = it.get("year") or ""
        year_txt = f"{year} " if year else ""
        mk, md = it.get("make"), it.get("model")
        score = it.get("score")
        price = it.get("price_best")
        src = it.get("price_source") or "—"
        price_txt = f" | {price} • {src}" if price else ""
        print(f"{i}. {year_txt}{mk} {md} | score={score}{price_txt}")

        # מציגים עד 3 סיבות, כך שהראשונות יקשרו ישירות לתשובות (כולל שנתון אם קיים)
        reasons = (it.get("reasons") or [])[:3]
        for r in reasons:
            print("   -", r)

def main():
    BASE = {
        "condition": "any",
        "usage": "mixed",
        "passengers": 4,
        "terrain": "flat",
        "budget_usd": 30000,
        "fuel_type": "any",
    }

    # A) מעט נסועה + אחזקה ארוכה => MPG↓ (אם לא הוגדר ידנית), דגש אמינות
    show_case(
        "Low annual_km + Long ownership (MPG↓, Reliability↑)",
        {**BASE, "annual_km": 8000, "ownership_years": 6, "prioritize_safety": True}
    )

    # B) נסועה גבוהה + אחזקה קצרה => MPG↑, אמינות לא מודגשת
    show_case(
        "High annual_km + Short ownership (MPG↑, Reliability off)",
        {**BASE, "annual_km": 15000, "ownership_years": 3}
    )

    # C) פילטר BEV בלבד — לבדוק סינון דלק ואת הסיבות (טווח/יעילות)
    show_case(
        "Fuel filter: BEV only",
        {**BASE, "annual_km": 12000, "ownership_years": 3, "fuel_type": "bev"}
    )

    # D) תקציב קשיח נמוך — לראות ששומרים על ≤ תקציב
    show_case(
        "Budget <= $17k",
        {**BASE, "budget_usd": 17000, "annual_km": 12000, "ownership_years": 4}
    )

if __name__ == "__main__":
    main()