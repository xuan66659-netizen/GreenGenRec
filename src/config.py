from pathlib import Path

# Project root = GreenGenRec/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Input data paths
RAW_RECIPE_PATH = PROJECT_ROOT / "data" / "raw" / "RAW_recipes.csv"
RAW_INTERACTION_PATH = PROJECT_ROOT / "data" / "raw" / "RAW_interactions.csv"
CARBON_REFERENCE_PATH = PROJECT_ROOT / "data" / "external" / "food-emissions-supply-chain.csv"

# Output directories
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "outputs" / "preprocessing"
TABLE_DIR = REPORT_DIR / "tables"

# Preprocessing parameters
RATING_THRESHOLD = 4
USER_CORE = 5
ITEM_CORE = 5

# Use active-user subset to keep the course project computationally manageable.
# Set to None if you want to use all users after k-core filtering.
MAX_USERS = 5000

# For sequence recommendation, keep each user's most recent MAX_SEQ_LEN + 2 interactions.
# +2 means one validation target and one test target.
MAX_SEQ_LEN = 20

# Nutrition outlier clipping before health score normalization
NUTRITION_CLIP_LOWER_Q = 0.01
NUTRITION_CLIP_UPPER_Q = 0.99

RANDOM_SEED = 42


def ensure_project_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
