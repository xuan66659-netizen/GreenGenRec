import pandas as pd

from config import (
    NUTRITION_CLIP_LOWER_Q,
    NUTRITION_CLIP_UPPER_Q,
    PROCESSED_DIR,
    TABLE_DIR,
    ensure_project_dirs,
)
from utils import clip_by_quantile, minmax_normalize


NUTRITION_COLUMNS = [
    "calories",
    "total_fat",
    "sugar",
    "sodium",
    "protein",
    "saturated_fat",
    "carbohydrates",
]


def main() -> None:
    ensure_project_dirs()

    recipe_path = PROCESSED_DIR / "clean_recipes.csv"
    if not recipe_path.exists():
        raise FileNotFoundError("clean_recipes.csv not found. Please run build_sequences.py first.")

    recipes = pd.read_csv(recipe_path)

    missing_cols = [c for c in NUTRITION_COLUMNS if c not in recipes.columns]
    if missing_cols:
        raise ValueError(f"Missing nutrition columns: {missing_cols}")

    health = recipes[["item_id"] + NUTRITION_COLUMNS].copy()

    for col in NUTRITION_COLUMNS:
        health[f"{col}_clipped"] = clip_by_quantile(
            health[col],
            lower_q=NUTRITION_CLIP_LOWER_Q,
            upper_q=NUTRITION_CLIP_UPPER_Q,
        )
        health[f"{col}_norm"] = minmax_normalize(health[f"{col}_clipped"])

    health["low_calorie"] = 1 - health["calories_norm"]
    health["low_sugar"] = 1 - health["sugar_norm"]
    health["low_sodium"] = 1 - health["sodium_norm"]
    health["low_saturated_fat"] = 1 - health["saturated_fat_norm"]

    health["health_score"] = (
        0.30 * health["protein_norm"]
        + 0.20 * health["low_calorie"]
        + 0.20 * health["low_sugar"]
        + 0.20 * health["low_sodium"]
        + 0.10 * health["low_saturated_fat"]
    )

    output_columns = [
        "item_id",
        "health_score",
        "protein_norm",
        "calories_norm",
        "sugar_norm",
        "sodium_norm",
        "saturated_fat_norm",
        "low_calorie",
        "low_sugar",
        "low_sodium",
        "low_saturated_fat",
    ]

    output = health[output_columns].copy()
    output.to_csv(PROCESSED_DIR / "item_health.csv", index=False, encoding="utf-8-sig")

    summary = output["health_score"].describe().reset_index()
    summary.columns = ["statistic", "value"]
    summary.to_csv(TABLE_DIR / "health_score_summary.csv", index=False, encoding="utf-8-sig")

    print("Health score construction finished.")
    print(f"Saved: {PROCESSED_DIR / 'item_health.csv'}")


if __name__ == "__main__":
    main()
