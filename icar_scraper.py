import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.icar.co.il"

def get_manufacturers():
    url = BASE_URL
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # מצא את כל הקישורים שבתוך תפריט היצרנים
    links = soup.select("a[href^='/car/']")
    manufacturers = set()

    for link in links:
        href = link["href"]
        parts = href.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "car":  # לדוגמה: /car/honda/
            manufacturers.add(parts[1])

    return list(manufacturers)

def get_models_for_manufacturer(manufacturer):
    url = f"{BASE_URL}/car/{manufacturer}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    model_links = soup.select("a[href^='/car/{}/']".format(manufacturer))
    return list(set(link.text.strip() for link in model_links))

if __name__ == "__main__":
    manufacturers = get_manufacturers()
    print("✅ Found manufacturers:", manufacturers)

    for manu in manufacturers[:5]:  # לבדיקה: רק 5 ראשונים
        print(f"\n🔍 Models for {manu}:")
        try:
            models = get_models_for_manufacturer(manu)
            for m in models:
                print(" -", m)
        except Exception as e:
            print("❌ Error fetching models for", manu, ":", e)
