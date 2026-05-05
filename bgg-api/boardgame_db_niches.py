from __future__ import annotations

import json
import os
from collections import defaultdict
import ast

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
            props = json.loads(row["properties"]) if pd.notna(row.get("properties")) else []
            # Use sorted tuple as key for reliable comparison
            props_key = tuple(sorted(props))
            existing_niches_by_properties[props_key] = {
                "name": row.get("name", "") if pd.notna(row.get("name", "")) else "",
                "description": row.get("description", "") if pd.notna(row.get("description", "")) else "",
            }

    niche_rows = []
    game_to_niches = defaultdict(list)

    for i, niche in enumerate(niches):
        _cluster_set, _niche_props, selected, qualifying_games = niche
        properties = selected if selected is not None else []
        games_list = [gid for gid, _, _, _ in qualifying_games]

        # Determine public name: prefer existing name, otherwise generate default
        props_key = tuple(sorted(properties))
        existing_metadata = existing_niches_by_properties.get(props_key, {})
        name = (existing_metadata.get("name") or "").strip()
        if not name:
            name = f"niche_{i + 1}"

        for gid in games_list:
            game_to_niches[str(gid)].append(name)

        niche_rows.append(
            {
                "name": name,
                "description": existing_metadata.get("description", ""),
                "properties": json.dumps(properties, ensure_ascii=False),
                "games_count": len(games_list),
            }
        )

    niches_df = pd.DataFrame(niche_rows, columns=["name", "description", "properties", "games_count"])
    niches_df.to_csv(niche_csv_path, index=False)

    updated_df_games = df_games.copy()
    updated_df_games["niches"] = updated_df_games["id"].apply(lambda gid: game_to_niches.get(str(gid), []))
    return updated_df_games


def build_niche_name_cache(
    df_games: pd.DataFrame,
    niche_csv_path: str = "data/niches.csv",
) -> dict[str, dict]:
    """Build in-memory cache: niche name -> niche metadata + games list."""
    niche_metadata: dict[str, dict] = {}
    if os.path.exists(niche_csv_path):
        try:
            niches_df = pd.read_csv(niche_csv_path)
            for _, row in niches_df.iterrows():
                name = str(row.get("name", "") or "").strip()
                if not name:
                    continue
                try:
                    properties = json.loads(row.get("properties") or "[]")
                except Exception:
                    properties = []

                niche_metadata[name] = {
                    "name": name,
                    "description": row.get("description", "") if pd.notna(row.get("description", "")) else "",
                    "properties": properties,
                    "games_count": int(row.get("games_count", 0)) if pd.notna(row.get("games_count", 0)) else 0,
                }
        except Exception:
            niche_metadata = {}

    games_ids_by_niche: defaultdict[str, list] = defaultdict(list)
    if not df_games.empty and "niches" in df_games.columns:
        for _, game_row in df_games.iterrows():
            gid = str(game_row.get("id", ""))
            for niche_name in _normalize_to_list(game_row.get("niches")):
                name = str(niche_name).strip()
                if not name:
                    continue
                games_ids_by_niche[name].append(gid)

    cache: dict[str, dict] = {}
    for name, meta in niche_metadata.items():
        games_ids = games_ids_by_niche.get(name, [])
        cache[name] = {
            "name": name,
            "description": meta.get("description", ""),
            "properties": meta.get("properties", []),
            "games_count": len(games_ids) if games_ids else meta.get("games_count", 0),
            "games_ids": games_ids,
        }

    # Include niches present on games but missing from CSV metadata.
    for name, games_ids in games_ids_by_niche.items():
        if name not in cache:
            cache[name] = {
                "name": name,
                "description": "",
                "properties": [],
                "games_count": len(games_ids),
                "games_ids": games_ids,
            }

    return cache


def _normalize_to_list(value) -> list:
    """Normalize a dataframe cell that might contain a list or stringified list."""
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [s]
        return [s]
    return [value]