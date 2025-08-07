import requests
import json

def get_models_by_make(make_name):
    """
    מחזיר רשימת דגמים לפי שם יצרן מ-CarQuery API עם טיפול בתגובה לא סטנדרטית
    """
    url = f"https://www.carqueryapi.com/api/0.3/?cmd=getModels&make={make_name.lower()}&callback="
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CarMatchAI/1.0; +https://yourproject.com)"
    }

    response = requests.get(url, headers=headers)
    raw_text = response.text.strip()

    # טיפול בתגובה שמתחילה ב- ({"Models": ...});
    if raw_text.startswith("(") and raw_text.endswith(");"):
        raw_text = raw_text[1:-2]  # מסיר סוגריים והנקודה-פסיק

    try:
        data = json.loads(raw_text)
    except Exception as e:
        print("❌ JSON parsing error:", e)
        return []

    results = data.get("Models", [])
    models = sorted(set(model["model_name"] for model in results if "model_name" in model))
    return models


# בדיקה
if __name__ == "__main__":
    make = "lamborghini"
    models = get_models_by_make(make)
    print(f"✅ Models for {make}:\n{models}")
