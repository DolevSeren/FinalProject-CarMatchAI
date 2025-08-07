import json

def load_model_translations(filepath="expanded_model_translation.json"):
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

def translate_model_to_hebrew(model_name, translations):
    return translations.get(model_name)
