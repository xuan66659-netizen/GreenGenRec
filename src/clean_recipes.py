from pathlib import Path

import numpy as np
import pandas as pd

from config import PROCESSED_DIR, RAW_RECIPE_PATH, TABLE_DIR, ensure_project_dirs
from utils import list_to_json, normalize_list_field, normalize_text, safe_literal_eval, save_json


NUTRITION_COLUMNS = [
    "calories",
    "total_fat",
    "sugar",
    "sodium",
    "protein",
    "saturated_fat",
    "carbohydrates",
]


CORE_RECIPE_COLUMNS = [
    "id",
    "name",
    "minutes",
    "tags",
    "nutrition",
    "n_steps",
    "steps",
    "description",
    "ingredients",
    "n_ingredients",
]


def parse_nutrition(value):
    parsed = safe_literal_eval(value)

    if not isinstance(parsed, list):
        return [np.nan] * 7

    if len(parsed) < 7:
        parsed = parsed + [np.nan] * (7 - len(parsed))

    parsed = parsed[:7]
    output = []

    for item in parsed:
        try:
            output.append(float(item))
        except Exception:
            output.append(np.nan)

    return output


def main() -> None:
    ensure_project_dirs()

    if not RAW_RECIPE_PATH.exists():
        raise FileNotFoundError(f"RAW_recipes.csv not found: {RAW_RECIPE_PATH}")

    print(f"Reading recipes from: {RAW_RECIPE_PATH}")
    recipes = pd.read_csv(RAW_RECIPE_PATH)

    original_rows = len(recipes)

    missing_cols = [c for c in CORE_RECIPE_COLUMNS if c not in recipes.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in RAW_recipes.csv: {missing_cols}")

    recipes = recipes[CORE_RECIPE_COLUMNS].copy()
    recipes = recipes.rename(columns={"id": "raw_recipe_id"})

    before_dedup = len(recipes)
    recipes = recipes.drop_duplicates(subset=["raw_recipe_id"], keep="first")
    after_dedup = len(recipes)

    recipes["name"] = recipes["name"].apply(normalize_text)
    recipes["description"] = recipes["description"].apply(normalize_text)

    recipes["tags_list"] = recipes["tags"].apply(normalize_list_field)
    recipes["steps_list"] = recipes["steps"].apply(normalize_list_field)
    recipes["ingredients_list"] = recipes["ingredients"].apply(normalize_list_field)

    nutrition_values = recipes["nutrition"].apply(parse_nutrition)
    nutrition_df = pd.DataFrame(nutrition_values.tolist(), columns=NUTRITION_COLUMNS, index=recipes.index)
    recipes = pd.concat([recipes, nutrition_df], axis=1)

    recipes["minutes"] = pd.to_numeric(recipes["minutes"], errors="coerce")
    recipes["n_steps"] = pd.to_numeric(recipes["n_steps"], errors="coerce")
    recipes["n_ingredients"] = pd.to_numeric(recipes["n_ingredients"], errors="coerce")

    before_quality_filter = len(recipes)

    recipes = recipes[
        (recipes["name"].str.len() > 0)
        & (recipes["ingredients_list"].apply(len) > 0)
        & (recipes[NUTRITION_COLUMNS].notna().sum(axis=1) >= 4)
    ].copy()

    after_quality_filter = len(recipes)

    recipes["ingredients_json"] = recipes["ingredients_list"].apply(list_to_json)
    recipes["tags_json"] = recipes["tags_list"].apply(list_to_json)
    recipes["steps_json"] = recipes["steps_list"].apply(list_to_json)

    recipes["ingredients_text"] = recipes["ingredients_list"].apply(lambda xs: ", ".join(xs))
    recipes["tags_text"] = recipes["tags_list"].apply(lambda xs: ", ".join(xs))

    output_columns = [
        "raw_recipe_id",
        "name",
        "minutes",
        "n_steps",
        "n_ingredients",
        "description",
        "ingredients_json",
        "ingredients_text",
        "tags_json",
        "tags_text",
        "steps_json",
    ] + NUTRITION_COLUMNS

    clean_recipes_full = recipes[output_columns].copy()
    clean_recipes_full_path = PROCESSED_DIR / "clean_recipes_full.csv"
    clean_recipes_full.to_csv(clean_recipes_full_path, index=False, encoding="utf-8-sig")

    report = {
        "input_file": str(RAW_RECIPE_PATH),
        "output_file": str(clean_recipes_full_path),
        "original_rows": int(original_rows),
        "duplicate_recipe_id_removed": int(before_dedup - after_dedup),
        "quality_filter_removed": int(before_quality_filter - after_quality_filter),
        "final_rows": int(len(clean_recipes_full)),
        "nutrition_columns": NUTRITION_COLUMNS,
    }

    save_json(report, TABLE_DIR / "clean_recipes_report.json")

    print("Recipe cleaning finished.")
    print(f"Original rows: {original_rows}")
    print(f"Final rows: {len(clean_recipes_full)}")
    print(f"Saved: {clean_recipes_full_path}")


if __name__ == "__main__":
    main()
