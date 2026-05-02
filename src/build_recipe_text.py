import pandas as pd

from config import PROCESSED_DIR, ensure_project_dirs


def bucket_by_quantiles(series: pd.Series, low_label: str, medium_label: str, high_label: str) -> pd.Series:
    q1 = series.quantile(1 / 3)
    q2 = series.quantile(2 / 3)

    def label(value):
        if value <= q1:
            return low_label
        if value <= q2:
            return medium_label
        return high_label

    return series.apply(label)


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

    data = recipes[
        [
            "item_id",
            "name",
            "ingredients_text",
            "tags_text",
        ]
    ].copy()

    data = data.merge(
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
    data = data.merge(
        carbon[["item_id", "carbon_score", "carbon_level"]],
        on="item_id",
        how="left",
    )

    data["protein_bucket"] = bucket_by_quantiles(
        data["protein_norm"],
        low_label="low-protein",
        medium_label="medium-protein",
        high_label="high-protein",
    )
    data["calorie_bucket"] = bucket_by_quantiles(
        data["calories_norm"],
        low_label="low-calorie",
        medium_label="medium-calorie",
        high_label="high-calorie",
    )
    data["sugar_bucket"] = bucket_by_quantiles(
        data["sugar_norm"],
        low_label="low-sugar",
        medium_label="medium-sugar",
        high_label="high-sugar",
    )
    data["sodium_bucket"] = bucket_by_quantiles(
        data["sodium_norm"],
        low_label="low-sodium",
        medium_label="medium-sodium",
        high_label="high-sodium",
    )

    def build_text(row):
        parts = [
            str(row["name"]),
            f"ingredients: {row['ingredients_text']}",
            f"tags: {row['tags_text']}",
            (
                "nutrition: "
                f"{row['calorie_bucket']}, "
                f"{row['protein_bucket']}, "
                f"{row['sugar_bucket']}, "
                f"{row['sodium_bucket']}"
            ),
            f"carbon: {row['carbon_level']}",
        ]
        return "; ".join(parts)

    data["recipe_text"] = data.apply(build_text, axis=1)

    output = data[["item_id", "recipe_text"]].copy()
    output.to_csv(PROCESSED_DIR / "recipe_text.csv", index=False, encoding="utf-8-sig")

    print("Recipe text construction finished.")
    print(f"Saved: {PROCESSED_DIR / 'recipe_text.csv'}")


if __name__ == "__main__":
    main()
