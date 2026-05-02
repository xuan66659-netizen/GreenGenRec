from clean_recipes import main as clean_recipes_main
from clean_interactions import main as clean_interactions_main
from build_sequences import main as build_sequences_main
from build_health_score import main as build_health_score_main
from build_carbon_score import main as build_carbon_score_main
from build_constraints import main as build_constraints_main
from build_recipe_text import main as build_recipe_text_main


def main() -> None:
    print("\n[1/7] Cleaning recipes...")
    clean_recipes_main()

    print("\n[2/7] Cleaning interactions...")
    clean_interactions_main()

    print("\n[3/7] Building user sequences and train/valid/test splits...")
    build_sequences_main()

    print("\n[4/7] Building health scores...")
    build_health_score_main()

    print("\n[5/7] Building carbon scores...")
    build_carbon_score_main()

    print("\n[6/7] Building constraint labels...")
    build_constraints_main()

    print("\n[7/7] Building recipe text...")
    build_recipe_text_main()

    print("\nAll preprocessing steps finished.")


if __name__ == "__main__":
    main()
