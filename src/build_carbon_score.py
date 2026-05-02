import json
from typing import Dict, List

import pandas as pd

from config import CARBON_REFERENCE_PATH, PROCESSED_DIR, TABLE_DIR, ensure_project_dirs
from utils import json_to_list, minmax_normalize, save_json


# Relative carbon weights.
# These values are not exact life-cycle emissions.
# They are weak labels inspired by public food carbon footprint references.
CARBON_CATEGORY_CONFIG: Dict[str, Dict] = {
    "beef": {
        "keywords": ["beef", "steak", "ground beef", "sirloin"],
        "weight": 5.0,
    },
    "lamb": {
        "keywords": ["lamb", "mutton"],
        "weight": 5.0,
    },
    "pork": {
        "keywords": ["pork", "bacon", "ham", "sausage", "pepperoni"],
        "weight": 4.0,
    },
    "cheese": {
        "keywords": ["cheese", "cheddar", "mozzarella", "parmesan", "cream cheese"],
        "weight": 4.0,
    },
    "chicken": {
        "keywords": ["chicken", "turkey", "poultry"],
        "weight": 3.0,
    },
    "fish": {
        "keywords": ["fish", "salmon", "tuna", "cod", "shrimp"],
        "weight": 3.0,
    },
    "egg": {
        "keywords": ["egg", "eggs"],
        "weight": 2.5,
    },
    "dairy": {
        "keywords": ["milk", "yogurt", "butter", "cream"],
        "weight": 2.5,
    },
    "rice_pasta": {
        "keywords": ["rice", "pasta", "noodle", "noodles", "bread", "flour", "wheat"],
        "weight": 2.0,
    },
    "tofu_beans": {
        "keywords": ["tofu", "beans", "bean", "lentils", "lentil", "chickpea", "peas"],
        "weight": 1.0,
    },
    "vegetables": {
        "keywords": [
            "tomato", "onion", "carrot", "spinach", "broccoli",
            "mushroom", "lettuce", "cabbage", "pepper", "potato",
            "zucchini", "celery", "cucumber", "cauliflower",
        ],
        "weight": 1.0,
    },
    "fruit": {
        "keywords": [
            "apple", "banana", "orange", "lemon", "berry",
            "strawberry", "blueberry", "grape", "peach", "pear",
        ],
        "weight": 1.0,
    },
}

DEFAULT_CARBON_WEIGHT = 2.5


def match_carbon_categories(ingredients: List[str]) -> Dict:
    matched_categories = []
    matched_keywords = []
    weights = []

    joined = " | ".join(ingredients)

    for category, config in CARBON_CATEGORY_CONFIG.items():
        keywords = config["keywords"]
        category_matched = False

        for keyword in keywords:
            if keyword in joined:
                matched_keywords.append(keyword)
                category_matched = True

        if category_matched:
            matched_categories.append(category)
            weights.append(float(config["weight"]))

    if not weights:
        weights = [DEFAULT_CARBON_WEIGHT]

    return {
        "matched_categories": matched_categories,
        "matched_keywords": matched_keywords,
        "carbon_score_raw": sum(weights) / len(weights),
    }


def assign_carbon_level(series: pd.Series) -> pd.Series:
    q1 = series.quantile(1 / 3)
    q2 = series.quantile(2 / 3)

    def label(value):
        if value <= q1:
            return "low"
        if value <= q2:
            return "medium"
        return "high"

    return series.apply(label)


def main() -> None:
    ensure_project_dirs()

    recipe_path = PROCESSED_DIR / "clean_recipes.csv"
    if not recipe_path.exists():
        raise FileNotFoundError("clean_recipes.csv not found. Please run build_sequences.py first.")

    recipes = pd.read_csv(recipe_path)

    if "ingredients_json" not in recipes.columns:
        raise ValueError("ingredients_json column not found in clean_recipes.csv")

    rows = []
    for _, row in recipes.iterrows():
        item_id = int(row["item_id"])
        ingredients = json_to_list(row["ingredients_json"])
        matched = match_carbon_categories(ingredients)

        rows.append(
            {
                "item_id": item_id,
                "carbon_score_raw": matched["carbon_score_raw"],
                "matched_carbon_categories": json.dumps(matched["matched_categories"], ensure_ascii=False),
                "matched_carbon_keywords": json.dumps(matched["matched_keywords"], ensure_ascii=False),
            }
        )

    carbon = pd.DataFrame(rows)
    carbon["carbon_score"] = minmax_normalize(carbon["carbon_score_raw"])
    carbon["carbon_level"] = assign_carbon_level(carbon["carbon_score"])

    output_columns = [
        "item_id",
        "carbon_score",
        "carbon_score_raw",
        "carbon_level",
        "matched_carbon_categories",
        "matched_carbon_keywords",
    ]

    carbon[output_columns].to_csv(PROCESSED_DIR / "item_carbon.csv", index=False, encoding="utf-8-sig")

    # Save the weak-label dictionary for documentation.
    save_json(
        {
            "note": "Relative weak-label carbon dictionary. Not exact life-cycle carbon emissions.",
            "default_carbon_weight": DEFAULT_CARBON_WEIGHT,
            "carbon_category_config": CARBON_CATEGORY_CONFIG,
            "carbon_reference_file_exists": CARBON_REFERENCE_PATH.exists(),
            "carbon_reference_file": str(CARBON_REFERENCE_PATH),
        },
        PROCESSED_DIR / "carbon_dict.json",
    )

    level_summary = carbon["carbon_level"].value_counts().reset_index()
    level_summary.columns = ["carbon_level", "recipe_count"]
    level_summary.to_csv(TABLE_DIR / "carbon_level_summary.csv", index=False, encoding="utf-8-sig")

    print("Carbon score construction finished.")
    print(f"Saved: {PROCESSED_DIR / 'item_carbon.csv'}")
    print(f"Saved: {PROCESSED_DIR / 'carbon_dict.json'}")


if __name__ == "__main__":
    main()
