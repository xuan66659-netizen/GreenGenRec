import pandas as pd

from config import PROCESSED_DIR, RAW_INTERACTION_PATH, TABLE_DIR, ensure_project_dirs
from utils import save_json


CORE_INTERACTION_COLUMNS = [
    "user_id",
    "recipe_id",
    "date",
    "rating",
    "review",
]


def main() -> None:
    ensure_project_dirs()

    if not RAW_INTERACTION_PATH.exists():
        raise FileNotFoundError(f"RAW_interactions.csv not found: {RAW_INTERACTION_PATH}")

    clean_recipes_full_path = PROCESSED_DIR / "clean_recipes_full.csv"
    if not clean_recipes_full_path.exists():
        raise FileNotFoundError(
            "clean_recipes_full.csv not found. Please run clean_recipes.py first."
        )

    print(f"Reading interactions from: {RAW_INTERACTION_PATH}")
    interactions = pd.read_csv(RAW_INTERACTION_PATH)

    original_rows = len(interactions)

    missing_cols = [c for c in CORE_INTERACTION_COLUMNS if c not in interactions.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in RAW_interactions.csv: {missing_cols}")

    interactions = interactions[CORE_INTERACTION_COLUMNS].copy()

    interactions = interactions.rename(
        columns={
            "user_id": "raw_user_id",
            "recipe_id": "raw_recipe_id",
        }
    )

    interactions["raw_user_id"] = pd.to_numeric(interactions["raw_user_id"], errors="coerce")
    interactions["raw_recipe_id"] = pd.to_numeric(interactions["raw_recipe_id"], errors="coerce")
    interactions["rating"] = pd.to_numeric(interactions["rating"], errors="coerce")
    interactions["date"] = pd.to_datetime(interactions["date"], errors="coerce")

    before_missing_filter = len(interactions)
    interactions = interactions.dropna(subset=["raw_user_id", "raw_recipe_id", "rating", "date"]).copy()
    after_missing_filter = len(interactions)

    interactions["raw_user_id"] = interactions["raw_user_id"].astype(int)
    interactions["raw_recipe_id"] = interactions["raw_recipe_id"].astype(int)

    clean_recipes = pd.read_csv(clean_recipes_full_path, usecols=["raw_recipe_id"])
    valid_recipe_ids = set(clean_recipes["raw_recipe_id"].astype(int).tolist())

    before_recipe_filter = len(interactions)
    interactions = interactions[interactions["raw_recipe_id"].isin(valid_recipe_ids)].copy()
    after_recipe_filter = len(interactions)

    before_dedup = len(interactions)
    interactions = interactions.sort_values(["raw_user_id", "raw_recipe_id", "date"])
    interactions = interactions.drop_duplicates(subset=["raw_user_id", "raw_recipe_id"], keep="last")
    after_dedup = len(interactions)

    interactions = interactions.sort_values(["raw_user_id", "date", "raw_recipe_id"]).reset_index(drop=True)

    output_path = PROCESSED_DIR / "clean_interactions_full.csv"
    interactions.to_csv(output_path, index=False, encoding="utf-8-sig")

    report = {
        "input_file": str(RAW_INTERACTION_PATH),
        "output_file": str(output_path),
        "original_rows": int(original_rows),
        "missing_or_invalid_removed": int(before_missing_filter - after_missing_filter),
        "invalid_recipe_id_removed": int(before_recipe_filter - after_recipe_filter),
        "duplicate_user_recipe_removed": int(before_dedup - after_dedup),
        "final_rows": int(len(interactions)),
    }

    save_json(report, TABLE_DIR / "clean_interactions_report.json")

    print("Interaction cleaning finished.")
    print(f"Original rows: {original_rows}")
    print(f"Final rows: {len(interactions)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
