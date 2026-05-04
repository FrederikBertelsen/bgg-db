from __future__ import annotations

import json
import os
from collections import defaultdict

import pandas as pd


def create_and_persist_niches(
    df_games: pd.DataFrame,
    niches: list,
    niche_csv_path: str = "data/niches.csv",
) -> pd.DataFrame:
    """Persist niche metadata to CSV and return df_games with a `niches` column added."""
    os.makedirs(os.path.dirname(niche_csv_path), exist_ok=True)

    niche_rows = []
    game_to_niches = defaultdict(list)

    for i, niche in enumerate(niches):
        _cluster_set, _niche_props, selected, qualifying_games = niche
        niche_id = f"niche_{i + 1}"
        properties = selected if selected is not None else []
        games_list = [gid for gid, _, _, _ in qualifying_games]

        for gid in games_list:
            game_to_niches[str(gid)].append(niche_id)

        niche_rows.append(
            {
                "niche_id": niche_id,
                "name": "",
                "description": "",
                "properties": json.dumps(properties, ensure_ascii=False),
                "games_count": len(games_list),
            }
        )

    niches_df = pd.DataFrame(niche_rows, columns=["niche_id", "name", "description", "properties", "games_count"])
    niches_df.to_csv(niche_csv_path, index=False)

    updated_df_games = df_games.copy()
    updated_df_games["niches"] = updated_df_games["id"].apply(lambda gid: game_to_niches.get(str(gid), []))
    return updated_df_games