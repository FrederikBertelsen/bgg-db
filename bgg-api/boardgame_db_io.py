from __future__ import annotations

import glob
import hashlib
import json
import os
import pickle

import pandas as pd

from data_conversion import parse_json_like_columns


def get_data_files_signature(data_folder_path: str = "data/final/") -> tuple[int, str]:
    """Return (file_count, hash_of_sorted_filenames) for the data folder."""
    pattern = os.path.join(data_folder_path, "*.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        return 0, ""

    filenames = [os.path.basename(path) for path in files]
    signature_str = ",".join(filenames)
    file_hash = hashlib.md5(signature_str.encode()).hexdigest()
    return len(files), file_hash


def load_cache_manifest(manifest_path: str) -> dict | None:
    """Load a JSON cache manifest if it exists."""
    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, "r") as file:
            return json.load(file)
    except Exception:
        return None


def save_cache_manifest(manifest_path: str, manifest: dict) -> None:
    """Persist a JSON cache manifest."""
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as file:
        json.dump(manifest, file)


def load_cached_boardgame_state(cache_dir: str) -> dict | None:
    """Load the cached BoardGameDB state from pickle files."""
    try:
        with open(os.path.join(cache_dir, "df_games.pkl"), "rb") as file:
            df_games = pickle.load(file)
        with open(os.path.join(cache_dir, "mechanic_importances.pkl"), "rb") as file:
            mechanic_importances = pickle.load(file)
        with open(os.path.join(cache_dir, "niches.pkl"), "rb") as file:
            niches_cache = pickle.load(file)

        return {
            "df_games": df_games,
            "mechanic_importances": mechanic_importances,
            "niches_cache": niches_cache,
        }
    except Exception:
        return None


def save_cached_boardgame_state(cache_dir: str, state: dict) -> None:
    """Persist the cached BoardGameDB state to pickle files."""
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "df_games.pkl"), "wb") as file:
        pickle.dump(state["df_games"], file)

    with open(os.path.join(cache_dir, "mechanic_importances.pkl"), "wb") as file:
        pickle.dump(state["mechanic_importances"], file)

    with open(os.path.join(cache_dir, "niches.pkl"), "wb") as file:
        pickle.dump(state.get("niches_cache"), file)


def load_merged_data(data_folder_path: str = "data/final/") -> pd.DataFrame:
    """Load CSVs from the data folder and merge them in filename order."""
    pattern = os.path.join(data_folder_path, "*.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        raise ValueError(f"No CSV files found in {data_folder_path}")

    print("\nLoading Data:")

    base = pd.read_csv(files[0])
    base = parse_json_like_columns(base)
    if "id" not in base.columns:
        raise ValueError(f"CSV file {files[0]} does not contain required 'id' column")

    base["id"] = base["id"].astype(str)
    base = base.drop_duplicates(subset="id", keep="last").set_index("id")
    print(f"    Base dataset: {len(base)}   - '{files[0]}'")

    for file_path in files[1:]:
        update = pd.read_csv(file_path)
        update = parse_json_like_columns(update)
        if "id" not in update.columns:
            raise ValueError(f"CSV file {file_path} does not contain required 'id' column")

        update["id"] = update["id"].astype(str)
        update = update.drop_duplicates(subset="id", keep="last").set_index("id")
        base = update.combine_first(base)
        print(f"    Applied update: {len(update)}   -> {len(base)} - '{file_path}'")

    return base.reset_index()