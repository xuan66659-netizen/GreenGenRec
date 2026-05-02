import pandas as pd

from config import PROCESSED_DIR, TABLE_DIR, ensure_project_dirs
from utils import json_to_list


MEAT_KEYWORDS = [
    "beef", "steak", "ground beef", "sirloin",
    "lamb", "mutton",
    "pork", "bacon", "ham", "sausage", "pepperoni",
    "chicken", "turkey", "poultry",
    "fish", "salmon", "tuna", "cod", "shrimp",
]


def contains_keyword(ingredients, keywords):
    joined = " | ".join(ingredients)
    return int(any(keyword in joined for keyword in keywords))


def main() -> None:
    ensure_project_dirs()

    recipe_path = PROCESSED_DIR / "clean_recipes.csv"
    health_path = PROCESSED_DIR / "item_health.csv"
    carbon_path = PROCESSED_DIR / "item_carbon.csv"

    for path in [recipe_path, health_path, carbon_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    recipes = pd.read_csv(recipe_path)
    health = pd.read_csv(health_path)
    carbon = pd.read_csv(carbon_path)

    data = recipes[["item_id", "ingredients_json"]].copy()
    data["ingredients_list"] = data["ingredients_json"].apply(json_to_list)

    constraints = data[["item_id"]].copy()

    constraints["contains_beef"] = data["ingredients_list"].apply(
        lambda xs: contains_keyword(xs, ["beef", "steak", "ground beef", "sirloin"])
    )
    constraints["contains_pork"] = data["ingredients_list"].apply(
        lambda xs: contains_keyword(xs, ["pork", "bacon", "ham", "sausage", "pepperoni"])
    )
    constraints["contains_chicken"] = data["ingredients_list"].apply(
        lambda xs: contains_keyword(xs, ["chicken", "turkey", "poultry"])
    )
    constraints["contains_fish"] = data["ingredients_list"].apply(
        lambda xs: contains_keyword(xs, ["fish", "salmon", "tuna", "cod", "shrimp"])
    )
    constraints["contains_meat"] = data["ingredients_list"].apply(
        lambda xs: contains_keyword(xs, MEAT_KEYWORDS)
    )
    constraints["vegetarian_like"] = 1 - constraints["contains_meat"]

    constraints = constraints.merge(
        health[
            [
                "item_id",
                "protein_norm",
                "calories_norm",
                "sugar_norm",
                "sodium_norm",
                "health_score",
            ]
        ],
        on="item_id",
        how="left",
    )
    constraints = constraints.merge(
        carbon[["item_id", "carbon_score", "carbon_level"]],
        on="item_id",
        how="left",
    )

    protein_q70 = constraints["protein_norm"].quantile(0.70)
    calorie_q30 = constraints["calories_norm"].quantile(0.30)
    sugar_q30 = constraints["sugar_norm"].quantile(0.30)
    sodium_q30 = constraints["sodium_norm"].quantile(0.30)

    constraints["high_protein"] = (constraints["protein_norm"] >= protein_q70).astype(int)
    constraints["low_calorie"] = (constraints["calories_norm"] <= calorie_q30).astype(int)
    constraints["low_sugar"] = (constraints["sugar_norm"] <= sugar_q30).astype(int)
    constraints["low_sodium"] = (constraints["sodium_norm"] <= sodium_q30).astype(int)
    constraints["low_carbon"] = (constraints["carbon_level"] == "low").astype(int)

    output_columns = [
        "item_id",
        "contains_beef",
        "contains_pork",
        "contains_chicken",
        "contains_fish",
        "contains_meat",
        "vegetarian_like",
        "high_protein",
        "low_calorie",
        "low_sugar",
        "low_sodium",
        "low_carbon",
    ]

    constraints[output_columns].to_csv(PROCESSED_DIR / "item_constraints.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for col in output_columns:
        if col == "item_id":
            continue
        summary_rows.append(
            {
                "constraint_label": col,
                "positive_count": int(constraints[col].sum()),
                "positive_ratio": float(constraints[col].mean()),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(TABLE_DIR / "constraint_label_summary.csv", index=False, encoding="utf-8-sig")

    print("Constraint label construction finished.")
    print(f"Saved: {PROCESSED_DIR / 'item_constraints.csv'}")


if __name__ == "__main__":
    main()
