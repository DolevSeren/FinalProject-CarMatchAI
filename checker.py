import pandas as pd
from pathlib import Path

path = Path("data/catalog_us.parquet")
if not path.exists():
    raise SystemExit(f"❌ לא נמצא הקובץ: {path.resolve()}")

try:
    df = pd.read_parquet(path)  # דורש pyarrow או fastparquet מותקן
except ImportError as e:
    raise SystemExit(
        "❌ חסר מנוע Parquet.\n"
        "התקן אחד מהבאים והרץ שוב:\n"
        "  python -m pip install 'pandas[parquet]'\n"
        "או: python -m pip install pyarrow\n"
        "או: python -m pip install fastparquet\n"
        f"\nשגיאה מקורית: {e}"
    )

print("✅ נטען בהצלחה!\n")
print("עמודות קיימות:")
print(list(df.columns))

if "price" in df.columns:
    print("\n📊 סטטיסטיקות price:")
    print(df["price"].describe())
    print("\n🔎 דוגמאות:")
    cols = [c for c in ["make", "model", "year", "price"] if c in df.columns]
    print(df[cols].head(20).to_string(index=False))
else:
    print("\n⚠️ אין עמודת 'price' בקטלוג. ההתאמה לתקציב מבוססת כנראה על שדות אחרים.")
