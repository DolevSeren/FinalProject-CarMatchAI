# CarMatch AI

CarMatch AI is an **AI-powered car recommendation system** that helps users choose the best car based on their personal needs.  
The project combines **structured data (catalog, APIs, scraped prices)** with an **interactive LLM-based chatbot** to provide tailored recommendations.

---

## 🚀 Features
- **Interactive Chat / Form (Streamlit UI)** – users can either chat naturally or fill a form.
- **Matching Engine** – ranks cars by budget, passengers, fuel type, safety, MPG, and more.
- **US Catalog (~10.4k rows)** – built from NHTSA, FuelEconomy.gov, and enriched with scraped used car prices.
- **Scraping with Puppeteer** – automated browser-based scraper for used car prices from [cars.com].
- **LLM Integration** – Large Language Model guides the chat flow, confirms user input, and explains recommendations.
- **Regression Checks** – ensures changes to the engine don’t break past scenarios.

---

## 📂 Project Structure

```bash
FinalProject-CarMatchAI/
├── agent/
│   ├── orchestrator.py      # מחבר בין הצ'אט, ה־LLM והמנוע
│   ├── llm.py               # פונקציות תקשורת עם ה־LLM (שאלות, סיכומים, תיקונים)
│   ├── fetch_models.py      # הורדת דגמים מה־API החיצוני
│   ├── enrich_model.py      # הוספת נתוני בטיחות/צריכת דלק לדגמים
│   └── providers.py         # רישום ספקי המידע (NHTSA, FuelEconomy וכו')
│
├── app/
│   ├── main.py              # אפליקציית Streamlit – ממשק ראשי (Chat / Form)
│   ├── streamlit_app.py     # גרסה נוספת להרצה מקומית/דמו
│   └── __init__.py
│
├── matching/
│   ├── engine.py            # מנוע ההתאמה – ניקוד וסינון רכבים
│   ├── matcher.py           # מעטפת סביב engine (לא תמיד בשימוש ישיר)
│   ├── domain.py            # מחלקות נתונים – CarModel, UserProfile
│   └── __init__.py
│
├── scripts/
│   ├── build_catalog_us.py          # בניית הקטלוג הראשוני מארה"ב
│   ├── finalize_enriched_catalog.py # מיזוג מחירים ונתוני העשרה לקטלוג
│   ├── merge_scraped_used.py        # שילוב מחירי יד שניה (Puppeteer)
│   ├── puppeteer/                   # קוד Node.js שמריץ scraping ב־cars.com
│   │   └── scrape_used.js           # סקרייפר בפועל
│   ├── regression_checks.py         # בדיקות רגרסיה לשמירת אמינות המנוע
│   ├── quick_check_catalog.py       # בדיקה ידנית של הקטלוג
│   └── checker.py                   # סקריפט בדיקות כללי
│
├── data/
│   ├── catalog_us.parquet   # דאטהבייס ראשי (10.4k רכבים, 2018–2026)
│   ├── *.csv                # קבצי ביניים (scraping, merge)
│   └── *.cache.json         # קבצי cache מ־API
│
├── tests/                   # בדיקות יחידה ואינטגרציה
│
├── .gitignore               # מתעלם מקבצי data כבדים וסודות
├── requirements.txt         # ספריות Python נחוצות
└── README.md