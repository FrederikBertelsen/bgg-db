from __future__ import annotations

import os
import pandas as pd
from recommender_v2 import _ensure_list

def clear_cache() -> None:
    print("\nClearing cache folder...\n")
    path = "data/cache"
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    if os.path.exists("data/mechanic_importances.csv"):
        os.remove("data/mechanic_importances.csv")


def collect_unique_values(df_games: pd.DataFrame, column: str) -> set[str]:
    """Return the set of unique normalized values from a list-like dataframe column."""
    unique_values: set[str] = set()
    if column not in df_games.columns:
        return unique_values

    for values in df_games[column].dropna():
        unique_values.update(_ensure_list(values))

    return unique_values