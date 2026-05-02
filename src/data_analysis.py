from pathlib import Path
import ast
import json
import re
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_RECIPE_PATH = PROJECT_ROOT / "data" / "raw" / "RAW_recipes.csv"
RAW_INTERACTION_PATH = PROJECT_ROOT / "data" / "raw" / "RAW_interactions.csv"
CARBON_PATH = PROJECT_ROOT / "data" / "external" / "food-emissions-supply-chain.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "data_analysis"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_PATH = OUTPUT_DIR / "data_analysis_report.md"


NUTRITION_COLUMNS = [
    "calories",
    "total_fat",
    "sugar",
    "sodium",
    "protein",
    "saturated_fat",
    "carbohydrates",
]


CARBON_KEYWORDS = {
    "beef": ["beef", "steak", "ground beef", "sirloin"],
    "lamb": ["lamb", "mutton"],
    "pork": ["pork", "bacon", "ham", "sausage", "pepperoni"],
    "cheese": ["cheese", "cheddar", "mozzarella", "parmesan", "cream cheese"],
    "chicken": ["chicken", "turkey", "poultry"],
    "fish": ["fish", "salmon", "tuna", "cod", "shrimp"],
    "egg": ["egg", "eggs"],
    "rice_pasta": ["rice", "pasta", "noodle", "noodles", "bread", "flour"],
    "tofu_beans": ["tofu", "beans", "bean", "lentils", "lentil", "chickpea", "peas"],
    "vegetables": [
        "tomato", "onion", "carrot", "spinach", "broccoli",
        "mushroom", "lettuce", "cabbage", "pepper", "potato"
    ],
    "fruit": ["apple", "banana", "orange", "lemon", "berry", "strawberry", "blueberry"],
}


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def safe_literal_eval(value):
    if pd.isna(value):
        return None
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return ast.literal_eval(value)
    except Exception:
        return None


def parse_list_field(value):
    parsed = safe_literal_eval(value)
    if not isinstance(parsed, list):
        return []
    return [str(x).strip().lower() for x in parsed if str(x).strip()]


def parse_nutrition(value):
    parsed = safe_literal_eval(value)
    if not isinstance(parsed, list):
        return [np.nan] * 7

    if len(parsed) < 7:
        parsed = parsed + [np.nan] * (7 - len(parsed))

    parsed = parsed[:7]
    output = []

    for x in parsed:
        try:
            output.append(float(x))
        except Exception:
            output.append(np.nan)

    return output


def save_table(df: pd.DataFrame, filename: str) -> None:
    path = TABLE_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[TABLE] saved: {path}")


def save_figure(filename: str) -> None:
    path = FIGURE_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    print(f"[FIGURE] saved: {path}")


def plot_bar(df, x_col, y_col, title, xlabel, ylabel, filename, rotation=45):
    plt.figure(figsize=(10, 6))
    plt.bar(df[x_col].astype(str), df[y_col])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    save_figure(filename)


def plot_hist(series, title, xlabel, ylabel, filename, bins=50, log_y=False):
    clean = series.dropna()
    plt.figure(figsize=(10, 6))
    plt.hist(clean, bins=bins)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    if log_y:
        plt.yscale("log")
    save_figure(filename)


def analyze_basic_info(recipes, interactions, carbon):
    rows = []

    rows.append({
        "dataset": "RAW_recipes",
        "rows": len(recipes),
        "columns": len(recipes.columns),
        "column_names": ", ".join(recipes.columns),
    })

    rows.append({
        "dataset": "RAW_interactions",
        "rows": len(interactions),
        "columns": len(interactions.columns),
        "column_names": ", ".join(interactions.columns),
    })

    if carbon is not None:
        rows.append({
            "dataset": "food_emissions_supply_chain",
            "rows": len(carbon),
            "columns": len(carbon.columns),
            "column_names": ", ".join(carbon.columns),
        })

    basic_info = pd.DataFrame(rows)
    save_table(basic_info, "01_basic_dataset_info.csv")
    return basic_info


def analyze_missing_values(df, dataset_name):
    missing = pd.DataFrame({
        "column": df.columns,
        "missing_count": df.isna().sum().values,
        "missing_rate": df.isna().mean().values,
    })
    missing = missing.sort_values("missing_rate", ascending=False)
    save_table(missing, f"02_missing_values_{dataset_name}.csv")
    return missing


def analyze_recipes(recipes):
    required_cols = ["id", "name", "minutes", "tags", "nutrition", "steps", "ingredients", "n_ingredients"]
    existing_cols = [c for c in required_cols if c in recipes.columns]

    recipe_summary = []

    recipe_summary.append({
        "metric": "recipe_rows",
        "value": len(recipes),
    })

    if "id" in recipes.columns:
        recipe_summary.append({
            "metric": "unique_recipe_id",
            "value": recipes["id"].nunique(),
        })

        recipe_summary.append({
            "metric": "duplicated_recipe_id",
            "value": recipes["id"].duplicated().sum(),
        })

    if "name" in recipes.columns:
        recipe_summary.append({
            "metric": "missing_name_count",
            "value": recipes["name"].isna().sum(),
        })

    if "ingredients" in recipes.columns:
        ingredients_list = recipes["ingredients"].apply(parse_list_field)
        ingredient_counts = ingredients_list.apply(len)

        recipe_summary.append({
            "metric": "recipes_with_empty_ingredients",
            "value": int((ingredient_counts == 0).sum()),
        })

        recipe_summary.append({
            "metric": "avg_ingredient_count",
            "value": float(ingredient_counts.mean()),
        })

        recipe_summary.append({
            "metric": "median_ingredient_count",
            "value": float(ingredient_counts.median()),
        })

        plot_hist(
            ingredient_counts,
            title="Distribution of Number of Ingredients",
            xlabel="Number of Ingredients",
            ylabel="Number of Recipes",
            filename="01_recipe_ingredient_count_distribution.png",
            bins=50,
            log_y=False,
        )

        all_ingredients = []
        for xs in ingredients_list:
            all_ingredients.extend(xs)

        top_ingredients = pd.DataFrame(
            Counter(all_ingredients).most_common(50),
            columns=["ingredient", "count"]
        )
        save_table(top_ingredients, "03_top_ingredients.csv")

        plot_bar(
            top_ingredients.head(20),
            x_col="ingredient",
            y_col="count",
            title="Top 20 Ingredients",
            xlabel="Ingredient",
            ylabel="Count",
            filename="02_top_20_ingredients.png",
        )

    if "tags" in recipes.columns:
        tags_list = recipes["tags"].apply(parse_list_field)
        tag_counts = tags_list.apply(len)

        recipe_summary.append({
            "metric": "recipes_with_empty_tags",
            "value": int((tag_counts == 0).sum()),
        })

        all_tags = []
        for xs in tags_list:
            all_tags.extend(xs)

        top_tags = pd.DataFrame(
            Counter(all_tags).most_common(50),
            columns=["tag", "count"]
        )
        save_table(top_tags, "04_top_tags.csv")

        plot_bar(
            top_tags.head(20),
            x_col="tag",
            y_col="count",
            title="Top 20 Tags",
            xlabel="Tag",
            ylabel="Count",
            filename="03_top_20_tags.png",
        )

    if "minutes" in recipes.columns:
        minutes = pd.to_numeric(recipes["minutes"], errors="coerce")

        recipe_summary.append({
            "metric": "minutes_missing_count",
            "value": int(minutes.isna().sum()),
        })

        recipe_summary.append({
            "metric": "minutes_mean",
            "value": float(minutes.mean()),
        })

        recipe_summary.append({
            "metric": "minutes_median",
            "value": float(minutes.median()),
        })

        recipe_summary.append({
            "metric": "minutes_99_percentile",
            "value": float(minutes.quantile(0.99)),
        })

        plot_hist(
            minutes.clip(upper=minutes.quantile(0.99)),
            title="Distribution of Cooking Time, Clipped at 99th Percentile",
            xlabel="Minutes",
            ylabel="Number of Recipes",
            filename="04_minutes_distribution_clipped.png",
            bins=50,
        )

    recipe_summary_df = pd.DataFrame(recipe_summary)
    save_table(recipe_summary_df, "05_recipe_summary.csv")

    return recipe_summary_df


def analyze_nutrition(recipes):
    if "nutrition" not in recipes.columns:
        print("[WARN] nutrition column not found in RAW_recipes.csv")
        return None

    nutrition_values = recipes["nutrition"].apply(parse_nutrition)
    nutrition_df = pd.DataFrame(nutrition_values.tolist(), columns=NUTRITION_COLUMNS)

    summary_rows = []

    for col in NUTRITION_COLUMNS:
        s = nutrition_df[col]

        summary_rows.append({
            "nutrition_field": col,
            "missing_count": int(s.isna().sum()),
            "missing_rate": float(s.isna().mean()),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()),
            "min": float(s.min()),
            "p01": float(s.quantile(0.01)),
            "p25": float(s.quantile(0.25)),
            "p50": float(s.quantile(0.50)),
            "p75": float(s.quantile(0.75)),
            "p99": float(s.quantile(0.99)),
            "max": float(s.max()),
        })

        clipped = s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
        plot_hist(
            clipped,
            title=f"Distribution of {col}, Clipped at 1%-99%",
            xlabel=col,
            ylabel="Number of Recipes",
            filename=f"05_nutrition_{col}_distribution.png",
            bins=50,
        )

    nutrition_summary = pd.DataFrame(summary_rows)
    save_table(nutrition_summary, "06_nutrition_summary.csv")

    return nutrition_summary


def analyze_interactions(interactions, recipes):
    interaction_summary = []

    interaction_summary.append({
        "metric": "interaction_rows",
        "value": len(interactions),
    })

    if "user_id" in interactions.columns:
        interaction_summary.append({
            "metric": "unique_users",
            "value": interactions["user_id"].nunique(),
        })

    if "recipe_id" in interactions.columns:
        interaction_summary.append({
            "metric": "unique_interacted_recipes",
            "value": interactions["recipe_id"].nunique(),
        })

    if "rating" in interactions.columns:
        ratings = pd.to_numeric(interactions["rating"], errors="coerce")

        interaction_summary.append({
            "metric": "rating_missing_count",
            "value": int(ratings.isna().sum()),
        })

        interaction_summary.append({
            "metric": "rating_mean",
            "value": float(ratings.mean()),
        })

        rating_dist = ratings.value_counts(dropna=False).sort_index().reset_index()
        rating_dist.columns = ["rating", "count"]
        rating_dist["ratio"] = rating_dist["count"] / rating_dist["count"].sum()
        save_table(rating_dist, "07_rating_distribution.csv")

        plot_bar(
            rating_dist,
            x_col="rating",
            y_col="count",
            title="Rating Distribution",
            xlabel="Rating",
            ylabel="Count",
            filename="06_rating_distribution.png",
            rotation=0,
        )

        positive = interactions[ratings >= 4].copy()
        interaction_summary.append({
            "metric": "positive_interactions_rating_ge_4",
            "value": len(positive),
        })

        interaction_summary.append({
            "metric": "positive_interaction_ratio",
            "value": float(len(positive) / len(interactions)),
        })
    else:
        positive = interactions.copy()

    if "date" in interactions.columns:
        date_series = pd.to_datetime(interactions["date"], errors="coerce")
        interaction_summary.append({
            "metric": "date_missing_or_invalid_count",
            "value": int(date_series.isna().sum()),
        })

        if date_series.notna().any():
            interaction_summary.append({
                "metric": "min_date",
                "value": str(date_series.min().date()),
            })
            interaction_summary.append({
                "metric": "max_date",
                "value": str(date_series.max().date()),
            })

            by_year = date_series.dt.year.value_counts().sort_index().reset_index()
            by_year.columns = ["year", "interaction_count"]
            save_table(by_year, "08_interactions_by_year.csv")

            plot_bar(
                by_year,
                x_col="year",
                y_col="interaction_count",
                title="Interactions by Year",
                xlabel="Year",
                ylabel="Interaction Count",
                filename="07_interactions_by_year.png",
                rotation=45,
            )

    summary_df = pd.DataFrame(interaction_summary)
    save_table(summary_df, "09_interaction_summary.csv")

    if "user_id" in positive.columns and "recipe_id" in positive.columns:
        user_counts = positive.groupby("user_id").size().reset_index(name="positive_interaction_count")
        recipe_counts = positive.groupby("recipe_id").size().reset_index(name="positive_interaction_count")

        user_count_summary = user_counts["positive_interaction_count"].describe(
            percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
        ).reset_index()
        user_count_summary.columns = ["statistic", "value"]
        save_table(user_count_summary, "10_user_positive_interaction_count_summary.csv")

        recipe_count_summary = recipe_counts["positive_interaction_count"].describe(
            percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
        ).reset_index()
        recipe_count_summary.columns = ["statistic", "value"]
        save_table(recipe_count_summary, "11_recipe_positive_interaction_count_summary.csv")

        plot_hist(
            user_counts["positive_interaction_count"].clip(
                upper=user_counts["positive_interaction_count"].quantile(0.99)
            ),
            title="User Positive Interaction Count Distribution, Clipped at 99th Percentile",
            xlabel="Positive Interactions per User",
            ylabel="Number of Users",
            filename="08_user_interaction_count_distribution.png",
            bins=50,
            log_y=True,
        )

        plot_hist(
            recipe_counts["positive_interaction_count"].clip(
                upper=recipe_counts["positive_interaction_count"].quantile(0.99)
            ),
            title="Recipe Popularity Distribution, Clipped at 99th Percentile",
            xlabel="Positive Interactions per Recipe",
            ylabel="Number of Recipes",
            filename="09_recipe_popularity_distribution.png",
            bins=50,
            log_y=True,
        )

        top_recipes = recipe_counts.sort_values("positive_interaction_count", ascending=False).head(50)
        save_table(top_recipes, "12_top_recipes_by_positive_interactions.csv")

        plot_bar(
            top_recipes.head(20),
            x_col="recipe_id",
            y_col="positive_interaction_count",
            title="Top 20 Recipes by Positive Interactions",
            xlabel="Recipe ID",
            ylabel="Positive Interaction Count",
            filename="10_top_20_popular_recipes.png",
        )

        total_users = user_counts["user_id"].nunique()
        total_items = recipe_counts["recipe_id"].nunique()
        total_positive = len(positive)

        sparsity = 1 - total_positive / (total_users * total_items)

        sparsity_df = pd.DataFrame([
            {
                "positive_users": total_users,
                "positive_items": total_items,
                "positive_interactions": total_positive,
                "sparsity": sparsity,
            }
        ])
        save_table(sparsity_df, "13_positive_feedback_sparsity.csv")

        kcore_rows = []
        for k in [3, 5, 10, 20]:
            user_keep = (user_counts["positive_interaction_count"] >= k).sum()
            item_keep = (recipe_counts["positive_interaction_count"] >= k).sum()

            kcore_rows.append({
                "k": k,
                "users_with_at_least_k_positive_interactions": int(user_keep),
                "recipes_with_at_least_k_positive_interactions": int(item_keep),
                "user_keep_ratio": float(user_keep / len(user_counts)),
                "recipe_keep_ratio": float(item_keep / len(recipe_counts)),
            })

        kcore_df = pd.DataFrame(kcore_rows)
        save_table(kcore_df, "14_kcore_threshold_reference.csv")

    return summary_df


def analyze_carbon_reference(carbon):
    if carbon is None:
        print("[WARN] carbon reference file not found")
        return None

    summary_rows = [
        {
            "metric": "carbon_reference_rows",
            "value": len(carbon),
        },
        {
            "metric": "carbon_reference_columns",
            "value": len(carbon.columns),
        },
        {
            "metric": "column_names",
            "value": ", ".join(carbon.columns),
        },
    ]

    carbon_summary = pd.DataFrame(summary_rows)
    save_table(carbon_summary, "15_carbon_reference_summary.csv")

    entity_col = None
    for candidate in ["Entity", "entity", "Food product", "food", "Food"]:
        if candidate in carbon.columns:
            entity_col = candidate
            break

    numeric_cols = carbon.select_dtypes(include=[np.number]).columns.tolist()

    if entity_col is not None:
        entity_values = carbon[entity_col].dropna().astype(str).sort_values()
        entity_df = pd.DataFrame({"carbon_reference_entity": entity_values})
        save_table(entity_df, "16_carbon_reference_entities.csv")

    if entity_col is not None and numeric_cols:
        numeric_summary = carbon[numeric_cols].describe().T.reset_index()
        numeric_summary = numeric_summary.rename(columns={"index": "numeric_column"})
        save_table(numeric_summary, "17_carbon_reference_numeric_summary.csv")

    return carbon_summary


def analyze_carbon_keyword_coverage(recipes):
    if "ingredients" not in recipes.columns:
        print("[WARN] ingredients column not found; skip carbon keyword coverage")
        return None

    ingredients_list = recipes["ingredients"].apply(parse_list_field)

    rows = []
    for category, keywords in CARBON_KEYWORDS.items():
        count = 0
        matched_examples = []

        for xs in ingredients_list:
            joined = " | ".join(xs)
            matched = any(keyword in joined for keyword in keywords)
            if matched:
                count += 1
                if len(matched_examples) < 5:
                    matched_examples.append(joined[:150])

        rows.append({
            "carbon_category": category,
            "recipe_count": count,
            "recipe_ratio": count / len(recipes),
            "keywords": ", ".join(keywords),
            "example_ingredients": " || ".join(matched_examples),
        })

    coverage_df = pd.DataFrame(rows).sort_values("recipe_count", ascending=False)
    save_table(coverage_df, "18_carbon_keyword_coverage_in_foodcom.csv")

    plot_bar(
        coverage_df,
        x_col="carbon_category",
        y_col="recipe_count",
        title="Carbon Keyword Coverage in Food.com Recipes",
        xlabel="Carbon Keyword Category",
        ylabel="Matched Recipe Count",
        filename="11_carbon_keyword_coverage.png",
    )

    return coverage_df


def write_markdown_report(
    basic_info,
    recipe_summary,
    nutrition_summary,
    interaction_summary,
    carbon_summary,
    carbon_coverage,
):
    lines = []

    lines.append("# Data Analysis Report")
    lines.append("")
    lines.append("This report summarizes the exploratory data analysis for the GreenGenRec project.")
    lines.append("")

    lines.append("## 1. Dataset Files")
    lines.append("")
    lines.append(f"- RAW_recipes.csv: `{RAW_RECIPE_PATH}`")
    lines.append(f"- RAW_interactions.csv: `{RAW_INTERACTION_PATH}`")
    lines.append(f"- Carbon reference CSV: `{CARBON_PATH}`")
    lines.append("")

    lines.append("## 2. Basic Dataset Information")
    lines.append("")
    lines.append(basic_info.to_markdown(index=False))
    lines.append("")

    lines.append("## 3. Recipe Data Summary")
    lines.append("")
    if recipe_summary is not None:
        lines.append(recipe_summary.to_markdown(index=False))
    lines.append("")

    lines.append("## 4. Nutrition Summary")
    lines.append("")
    if nutrition_summary is not None:
        lines.append(nutrition_summary.to_markdown(index=False))
    lines.append("")

    lines.append("## 5. Interaction Data Summary")
    lines.append("")
    if interaction_summary is not None:
        lines.append(interaction_summary.to_markdown(index=False))
    lines.append("")

    lines.append("## 6. Carbon Reference Summary")
    lines.append("")
    if carbon_summary is not None:
        lines.append(carbon_summary.to_markdown(index=False))
    lines.append("")

    lines.append("## 7. Carbon Keyword Coverage in Food.com")
    lines.append("")
    if carbon_coverage is not None:
        lines.append(carbon_coverage[["carbon_category", "recipe_count", "recipe_ratio", "keywords"]].to_markdown(index=False))
    lines.append("")

    lines.append("## 8. Notes for Later Preprocessing")
    lines.append("")
    lines.append("- Rating >= 4 can be used as positive feedback.")
    lines.append("- User/item k-core filtering should be considered because recommendation data is usually sparse and long-tailed.")
    lines.append("- Nutrition fields should be clipped before normalization because outliers may exist.")
    lines.append("- Carbon labels should be treated as weak labels, not exact life-cycle carbon emissions.")
    lines.append("- Recipe text can be built from name, ingredients, tags, nutrition buckets, and carbon level.")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[REPORT] saved: {REPORT_PATH}")


def main():
    ensure_dirs()

    if not RAW_RECIPE_PATH.exists():
        raise FileNotFoundError(f"Missing file: {RAW_RECIPE_PATH}")

    if not RAW_INTERACTION_PATH.exists():
        raise FileNotFoundError(f"Missing file: {RAW_INTERACTION_PATH}")

    print("Reading RAW_recipes.csv...")
    recipes = pd.read_csv(RAW_RECIPE_PATH)

    print("Reading RAW_interactions.csv...")
    interactions = pd.read_csv(RAW_INTERACTION_PATH)

    carbon = None
    if CARBON_PATH.exists():
        print("Reading carbon reference CSV...")
        carbon = pd.read_csv(CARBON_PATH)
    else:
        print(f"[WARN] Carbon reference CSV not found: {CARBON_PATH}")

    print("Running data analysis...")

    basic_info = analyze_basic_info(recipes, interactions, carbon)

    analyze_missing_values(recipes, "recipes")
    analyze_missing_values(interactions, "interactions")
    if carbon is not None:
        analyze_missing_values(carbon, "carbon_reference")

    recipe_summary = analyze_recipes(recipes)
    nutrition_summary = analyze_nutrition(recipes)
    interaction_summary = analyze_interactions(interactions, recipes)
    carbon_summary = analyze_carbon_reference(carbon)
    carbon_coverage = analyze_carbon_keyword_coverage(recipes)

    write_markdown_report(
        basic_info=basic_info,
        recipe_summary=recipe_summary,
        nutrition_summary=nutrition_summary,
        interaction_summary=interaction_summary,
        carbon_summary=carbon_summary,
        carbon_coverage=carbon_coverage,
    )

    print("\nData analysis finished.")
    print(f"Tables saved to: {TABLE_DIR}")
    print(f"Figures saved to: {FIGURE_DIR}")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()