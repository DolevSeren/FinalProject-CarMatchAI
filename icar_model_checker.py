import requests
import urllib.parse
from model_translation import translate_model_to_hebrew, load_model_translations


def build_icar_url(hebrew_name):
    parts = hebrew_name.split()
    base_name = "_".join(parts)
    manufacturer = parts[0]
    url = f"https://www.icar.co.il/{urllib.parse.quote(manufacturer)}/{urllib.parse.quote(base_name)}/{urllib.parse.quote(base_name)}_חדש/"
    return url


def check_icar_availability(model_name, translations):
    hebrew_name = translate_model_to_hebrew(model_name, translations)

    if not hebrew_name:
        print(f"❌ No Hebrew translation for: {model_name}")
        return

    print(f"\n🔍 בדיקה: {model_name} → {hebrew_name}")

    url = build_icar_url(hebrew_name)
    print(f"🔗 URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ נמצא בישראל בכתובת: {url}")
        else:
            print(f"❌ לא נמצא (status code: {response.status_code})")
    except Exception as e:
        print(f"❌ Error fetching URL: {e}")


if __name__ == "__main__":
    translations = load_model_translations("expanded_model_translation.json")

    # דגמים לדוגמה — תוכל לשנות/להרחיב כרצונך
    models = [
        "Mazda 3",
        "Honda Civic",
        "Toyota Corolla",
        "Kia Sportage",
        "Tesla Model Y",
        "BYD Atto 3",
        "Tesla Model 3",
        "Toyota Yaris Hybrid",
        "Honda Civic Hatchback",
        "Kia Sportage"
    ]

    for model in models:
        check_icar_availability(model, translations)
