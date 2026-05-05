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
    """Persist niche metadata to CSV and return df_games with a `niches` column added.
    
    Preserves existing names and descriptions for niches with unchanged properties.
    """
    os.makedirs(os.path.dirname(niche_csv_path), exist_ok=True)

    # Load existing niches and create a mapping from properties to metadata
    existing_niches_by_properties = {}
    if os.path.exists(niche_csv_path):
        existing_df = pd.read_csv(niche_csv_path)
        for _, row in existing_df.iterrows():
            props = json.loads(row["properties"])
            # Use sorted tuple as key for reliable comparison
            props_key = tuple(sorted(props))
            existing_niches_by_properties[props_key] = {
                "name": row["name"] if pd.notna(row["name"]) else "",
                "description": row["description"] if pd.notna(row["description"]) else "",
            }

    niche_rows = []
    game_to_niches = defaultdict(list)

    for i, niche in enumerate(niches):
        _cluster_set, _niche_props, selected, qualifying_games = niche
        niche_id = f"niche_{i + 1}"
        properties = selected if selected is not None else []
        games_list = [gid for gid, _, _, _ in qualifying_games]

        for gid in games_list:
            game_to_niches[str(gid)].append(niche_id)

        # Check if this property set already exists
        props_key = tuple(sorted(properties))
        existing_metadata = existing_niches_by_properties.get(props_key, {})

        niche_rows.append(
            {
                "niche_id": niche_id,
                "name": existing_metadata.get("name", ""),
                "description": existing_metadata.get("description", ""),
                "properties": json.dumps(properties, ensure_ascii=False),
                "games_count": len(games_list),
            }
        )

    niches_df = pd.DataFrame(niche_rows, columns=["niche_id", "name", "description", "properties", "games_count"])
    niches_df.to_csv(niche_csv_path, index=False)

    updated_df_games = df_games.copy()
    updated_df_games["niches"] = updated_df_games["id"].apply(lambda gid: game_to_niches.get(str(gid), []))
    return updated_df_games