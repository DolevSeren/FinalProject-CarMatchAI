# agent/orchestrator.py
import pandas as pd
from matching.engine import rank_cars
from collections import namedtuple

# מבנה פשוט לייצוג רכב
Car = namedtuple("Car", ["make", "model", "price_new_usd", "price_used_usd"])

def get_recommendations(answers, api_key=None):
    """
    ממיר את תשובות המשתמש לקריאה למנוע ההתאמה ומחזיר תוצאות.
    """
    # טען את הקטלוג
    df = pd.read_parquet("data/catalog_us.parquet")

    # סינון לפי סוג דלק אם נבחר
    fuel_type = answers.get("fuel_type", "any")
    if fuel_type and fuel_type.lower() != "any":
        df = df[df["fuelType"].str.lower().str.contains(fuel_type.lower(), na=False)]

    # קריאה למנוע ההתאמה
    ranked_df = rank_cars(
        df=df,
        usage=answers.get("usage", "mixed"),
        passengers=answers.get("passengers", 1),
        budget_usd=answers.get("budget_usd", 50000),
        comfort_priority=answers.get("comfort_priority", False),
        fun_priority=answers.get("fun_priority", False),
        terrain=answers.get("terrain", None),
        years_to_keep=answers.get("years_to_keep", 5),
        special_needs=answers.get("special_needs", []),
        condition=answers.get("condition", "any"),
        top_n=3,  # מגביל ל־3 תוצאות בלבד
        max_per_model=1,
        max_share_per_fuel=0.6
    )

    # המרה לאובייקטים פשוטים
    results = {}
    for cond in ["new", "used"]:
        if cond in ranked_df:
            results[cond] = [
                (
                    Car(
                        make=row["make"],
                        model=row["model"],
                        price_new_usd=row.get("price_new_usd", 0),
                        price_used_usd=row.get("price_used_usd", 0)
                    ),
                    round(row["score"], 3)
                )
                for _, row in ranked_df[cond].iterrows()
            ]

    return answers, results
