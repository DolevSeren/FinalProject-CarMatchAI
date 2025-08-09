
def parse_answers(answers):
    profile = {}

    # סוג הרכב: חדש / משומש
    raw = answers.get("Would you like a new or used car?")
    profile["car_type"] = raw.lower() if raw else None

    # תקציב
    raw = answers.get("What’s your maximum budget?")
    try:
        profile["budget_max"] = int(raw.replace(",", "").replace("₪", "").replace("$", "").strip())
    except:
        profile["budget_max"] = None

    # שימוש עיקרי
    raw = answers.get("What will you mostly use the car for?")
    profile["use_case"] = raw.lower() if raw else None

    # כמות נוסעים
    raw = answers.get("How many people usually ride in the car?")
    try:
        profile["passengers"] = int(raw.strip())
    except:
        profile["passengers"] = None

    # נסועה שנתית
    raw = answers.get("How many kilometers do you drive per year?")
    km_map = {
        "5-10k": 7500,
        "10-20k": 15000,
        "20-30k": 25000,
        "30k+": 35000
    }
    for key, val in km_map.items():
        if raw and key in raw:
            profile["annual_km"] = val
            break
    else:
        profile["annual_km"] = None

    # כמה שנים מתכנן להחזיק
    raw = answers.get("How long do you plan to keep the car?")
    profile["ownership_duration"] = raw

    # העדפות כלליות
    raw = answers.get("What are the top 2-3 things that matter most to you in a car?")
    profile["priorities"] = [x.strip().lower() for x in raw.split(",")] if raw else []

    # הסבר על "מה הכוונה שלך"
    profile["preference_explanation"] = answers.get("When you say something like 'sporty' or 'comfortable', what exactly do you mean?")

    # רכב נוכחי
    profile["current_car"] = answers.get("What car are you currently driving?")

    # אהבתי ברכב הנוכחי
    profile["likes"] = answers.get("What do you like about your current car?")

    # לא אהבתי ברכב הנוכחי
    profile["dislikes"] = answers.get("What do you dislike about your current car?")

    # צרכים מיוחדים
    profile["special_needs"] = answers.get("Any special needs or features you’re looking for?")

    print("PROFILE TO RETURN:", profile)
    return profile

