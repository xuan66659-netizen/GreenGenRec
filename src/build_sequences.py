from collections import defaultdict

import pandas as pd

from config import (
    ITEM_CORE,
    MAX_SEQ_LEN,
    MAX_USERS,
    PROCESSED_DIR,
    RATING_THRESHOLD,
    TABLE_DIR,
    USER_CORE,
    ensure_project_dirs,
)
from utils import save_json


def iterative_k_core(df: pd.DataFrame, user_col: str, item_col: str, user_core: int, item_core: int) -> pd.DataFrame:
    """Iteratively filter users/items until both user-core and item-core constraints are satisfied."""
    filtered = df.copy()

    while True:
        before = len(filtered)

        user_counts = filtered.groupby(user_col).size()
        valid_users = set(user_counts[user_counts >= user_core].index)
        filtered = filtered[filtered[user_col].isin(valid_users)].copy()

        item_counts = filtered.groupby(item_col).size()
        valid_items = set(item_counts[item_counts >= item_core].index)
        filtered = filtered[filtered[item_col].isin(valid_items)].copy()

        after = len(filtered)
        if after == before:
            break

    return filtered.reset_index(drop=True)


def keep_active_users(df: pd.DataFrame, max_users):
    if max_users is None:
        return df.copy()

    user_counts = df.groupby("raw_user_id").size().sort_values(ascending=False)
    selected_users = set(user_counts.head(max_users).index)
    return df[df["raw_user_id"].isin(selected_users)].copy()


def truncate_user_sequences(df: pd.DataFrame, max_seq_len: int) -> pd.DataFrame:
    """Keep each user's most recent max_seq_len + 2 interactions."""
    keep_len = max_seq_len + 2
    output = []

    for _, group in df.groupby("raw_user_id", sort=False):
        group = group.sort_values(["date", "raw_recipe_id"])
        if len(group) > keep_len:
            group = group.tail(keep_len)
        output.append(group)

    return pd.concat(output, ignore_index=True)


def main() -> None:
    ensure_project_dirs()

    interactions_path = PROCESSED_DIR / "clean_interactions_full.csv"
    recipes_path = PROCESSED_DIR / "clean_recipes_full.csv"

    if not interactions_path.exists():
        raise FileNotFoundError("clean_interactions_full.csv not found. Please run clean_interactions.py first.")
    if not recipes_path.exists():
        raise FileNotFoundError("clean_recipes_full.csv not found. Please run clean_recipes.py first.")

    interactions = pd.read_csv(interactions_path, parse_dates=["date"])
    recipes = pd.read_csv(recipes_path)

    original_rows = len(interactions)

    positive = interactions[interactions["rating"] >= RATING_THRESHOLD].copy()
    before_kcore = len(positive)

    filtered = iterative_k_core(
        positive,
        user_col="raw_user_id",
        item_col="raw_recipe_id",
        user_core=USER_CORE,
        item_core=ITEM_CORE,
    )
    after_kcore = len(filtered)

    filtered = keep_active_users(filtered, MAX_USERS)

    # After active user sampling, remove items that no longer satisfy item_core.
    filtered = iterative_k_core(
        filtered,
        user_col="raw_user_id",
        item_col="raw_recipe_id",
        user_core=USER_CORE,
        item_core=ITEM_CORE,
    )
    after_active_subset_and_kcore = len(filtered)

    filtered = filtered.sort_values(["raw_user_id", "date", "raw_recipe_id"]).reset_index(drop=True)
    filtered = truncate_user_sequences(filtered, MAX_SEQ_LEN)

    # Make sure every user still has at least 3 interactions for train/valid/test.
    seq_len = filtered.groupby("raw_user_id").size()
    valid_users = set(seq_len[seq_len >= 3].index)
    filtered = filtered[filtered["raw_user_id"].isin(valid_users)].copy()

    raw_user_ids = sorted(filtered["raw_user_id"].unique())
    raw_recipe_ids = sorted(filtered["raw_recipe_id"].unique())

    user_mapping = {
        "raw_to_user": {str(raw_id): idx for idx, raw_id in enumerate(raw_user_ids)},
        "user_to_raw": {str(idx): str(raw_id) for idx, raw_id in enumerate(raw_user_ids)},
    }

    item_mapping = {
        "raw_to_item": {str(raw_id): idx for idx, raw_id in enumerate(raw_recipe_ids)},
        "item_to_raw": {str(idx): str(raw_id) for idx, raw_id in enumerate(raw_recipe_ids)},
    }

    filtered["user_id"] = filtered["raw_user_id"].map(lambda x: user_mapping["raw_to_user"][str(x)])
    filtered["item_id"] = filtered["raw_recipe_id"].map(lambda x: item_mapping["raw_to_item"][str(x)])

    filtered = filtered.sort_values(["user_id", "date", "item_id"]).reset_index(drop=True)

    # Build filtered recipe table with continuous item_id.
    recipes_filtered = recipes[recipes["raw_recipe_id"].isin(raw_recipe_ids)].copy()
    recipes_filtered["item_id"] = recipes_filtered["raw_recipe_id"].map(lambda x: item_mapping["raw_to_item"][str(x)])
    recipes_filtered = recipes_filtered.sort_values("item_id").reset_index(drop=True)

    items = recipes_filtered[
        [
            "item_id",
            "raw_recipe_id",
            "name",
            "minutes",
            "n_ingredients",
            "ingredients_text",
            "tags_text",
        ]
    ].copy()

    # Split by user: train = all except last 2; valid = second last; test = last.
    train_rows = []
    valid_rows = []
    test_rows = []

    user_sequences = {}
    train_sequences = {}
    valid_targets = {}
    test_targets = {}

    for user_id, group in filtered.groupby("user_id", sort=True):
        group = group.sort_values(["date", "item_id"]).reset_index(drop=True)
        item_seq = group["item_id"].astype(int).tolist()

        user_sequences[str(user_id)] = item_seq

        train_group = group.iloc[:-2].copy()
        valid_group = group.iloc[[-2]].copy()
        test_group = group.iloc[[-1]].copy()

        train_sequences[str(user_id)] = train_group["item_id"].astype(int).tolist()
        valid_targets[str(user_id)] = int(valid_group["item_id"].iloc[0])
        test_targets[str(user_id)] = int(test_group["item_id"].iloc[0])

        train_rows.append(train_group)
        valid_rows.append(valid_group)
        test_rows.append(test_group)

    train = pd.concat(train_rows, ignore_index=True)
    valid = pd.concat(valid_rows, ignore_index=True)
    test = pd.concat(test_rows, ignore_index=True)

    columns = [
        "user_id",
        "item_id",
        "raw_user_id",
        "raw_recipe_id",
        "date",
        "rating",
        "review",
    ]

    filtered[columns].to_csv(PROCESSED_DIR / "positive_interactions.csv", index=False, encoding="utf-8-sig")
    train[columns].to_csv(PROCESSED_DIR / "train.csv", index=False, encoding="utf-8-sig")
    valid[columns].to_csv(PROCESSED_DIR / "valid.csv", index=False, encoding="utf-8-sig")
    test[columns].to_csv(PROCESSED_DIR / "test.csv", index=False, encoding="utf-8-sig")

    recipes_filtered.to_csv(PROCESSED_DIR / "clean_recipes.csv", index=False, encoding="utf-8-sig")
    items.to_csv(PROCESSED_DIR / "items.csv", index=False, encoding="utf-8-sig")

    save_json(user_mapping, PROCESSED_DIR / "user_id_mapping.json")
    save_json(item_mapping, PROCESSED_DIR / "item_id_mapping.json")
    save_json(user_sequences, PROCESSED_DIR / "user_sequences.json")
    save_json(train_sequences, PROCESSED_DIR / "train_sequences.json")
    save_json(valid_targets, PROCESSED_DIR / "valid_targets.json")
    save_json(test_targets, PROCESSED_DIR / "test_targets.json")

    summary = pd.DataFrame(
        [
            {"metric": "original_interactions_after_basic_cleaning", "value": original_rows},
            {"metric": "positive_interactions_rating_ge_threshold", "value": len(positive)},
            {"metric": "interactions_before_kcore", "value": before_kcore},
            {"metric": "interactions_after_initial_kcore", "value": after_kcore},
            {"metric": "interactions_after_active_user_subset_and_kcore", "value": after_active_subset_and_kcore},
            {"metric": "final_interactions_after_sequence_truncation", "value": len(filtered)},
            {"metric": "final_users", "value": filtered["user_id"].nunique()},
            {"metric": "final_items", "value": filtered["item_id"].nunique()},
            {"metric": "train_interactions", "value": len(train)},
            {"metric": "valid_interactions", "value": len(valid)},
            {"metric": "test_interactions", "value": len(test)},
            {"metric": "rating_threshold", "value": RATING_THRESHOLD},
            {"metric": "user_core", "value": USER_CORE},
            {"metric": "item_core", "value": ITEM_CORE},
            {"metric": "max_users", "value": MAX_USERS if MAX_USERS is not None else "None"},
            {"metric": "max_seq_len", "value": MAX_SEQ_LEN},
        ]
    )
    summary.to_csv(TABLE_DIR / "sequence_preprocessing_summary.csv", index=False, encoding="utf-8-sig")

    print("Sequence construction finished.")
    print(f"Final users: {filtered['user_id'].nunique()}")
    print(f"Final items: {filtered['item_id'].nunique()}")
    print(f"Final positive interactions: {len(filtered)}")
    print(f"Saved processed data to: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
