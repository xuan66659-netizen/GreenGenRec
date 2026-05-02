import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def safe_literal_eval(value: Any) -> Any:
    """Safely parse Python-list-like strings in Food.com CSV fields."""
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


def normalize_text(value: Any) -> str:
    """Lowercase and normalize whitespace."""
    if pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_list_field(value: Any) -> List[str]:
    """Parse and normalize a list-like field."""
    parsed = safe_literal_eval(value)
    if not isinstance(parsed, list):
        return []

    output = []
    for item in parsed:
        text = normalize_text(item)
        if text:
            output.append(text)
    return output


def list_to_json(values: Any) -> str:
    """Save list values safely into CSV cells."""
    if not isinstance(values, list):
        values = []
    return json.dumps(values, ensure_ascii=False)


def json_to_list(value: Any) -> List[str]:
    """Read list values previously saved as JSON strings."""
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        return []

    return []


def save_json(obj: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Min-max normalize a pandas Series. If constant, return zeros."""
    s = pd.to_numeric(series, errors="coerce")
    min_value = s.min()
    max_value = s.max()

    if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
        return pd.Series(np.zeros(len(s)), index=s.index)

    return (s - min_value) / (max_value - min_value)


def clip_by_quantile(series: pd.Series, lower_q: float = 0.01, upper_q: float = 0.99) -> pd.Series:
    """Clip extreme values using quantiles."""
    s = pd.to_numeric(series, errors="coerce")
    lower = s.quantile(lower_q)
    upper = s.quantile(upper_q)
    return s.clip(lower=lower, upper=upper)


def contains_any_keyword(text: str, keywords: List[str]) -> bool:
    """Simple keyword containment check."""
    if not isinstance(text, str):
        return False
    return any(keyword in text for keyword in keywords)
