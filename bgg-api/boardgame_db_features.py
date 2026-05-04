from __future__ import annotations

import pandas as pd

from recommender import _ensure_list


def collect_unique_values(df_games: pd.DataFrame, column: str) -> set[str]:
    """Return the set of unique normalized values from a list-like dataframe column."""
    unique_values: set[str] = set()
    if column not in df_games.columns:
        return unique_values

    for values in df_games[column].dropna():
        unique_values.update(_ensure_list(values))

    return unique_values