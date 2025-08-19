import pandas as pd

# טוען את הקובץ ששמרנו
df = pd.read_parquet("data/catalog_us.parquet")

print(len(df), "rows")
print(df.columns.tolist())

# מציג 5 דוגמאות עם עמודות מעניינות
print(df.sample(5)[[
    "year",
    "make",
    "model",
    "VClass",
    "fuelType",
    "MPG_comb",
    "overall_safety"
]])
