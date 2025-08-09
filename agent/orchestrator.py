# agent/orchestrator.py
from typing import Dict, Any
from matching.domain import UserProfile
from agent.providers import GlobalAPIProvider
from matching.matcher import filter_by_condition_and_budget, rank_cars

def build_user_profile(answers: Dict[str, Any]) -> UserProfile:
    return UserProfile(
        condition=answers.get("condition","any"),
        budget_usd=float(answers.get("budget_usd") or 0),
        passengers=int(answers.get("passengers", 1)),
        annual_km=answers.get("annual_km"),
        terrain=answers.get("terrain"),
        comfort_priority=bool(answers.get("comfort_priority")),
        fun_to_drive_priority=bool(answers.get("fun_priority")),
        years_to_keep=answers.get("years_to_keep"),
        special_needs=answers.get("special_needs", []),
    )

def get_recommendations(answers: Dict[str, Any], api_key: str):
    user = build_user_profile(answers)
    cars = GlobalAPIProvider(api_key).fetch()

    new_list, used_list = filter_by_condition_and_budget(cars, user)

    result = {}
    if user.condition in ("new", "any"):
        result["new"] = rank_cars(new_list, user)[:20]
    if user.condition in ("used", "any"):
        result["used"] = rank_cars(used_list, user)[:20]
    return user, result
