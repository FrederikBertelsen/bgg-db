from __future__ import annotations

from boardgame_db_io import (
    get_data_files_signature,
    load_cache_manifest,
    load_cached_boardgame_state,
    save_cache_manifest,
    save_cached_boardgame_state,
)


def prepare_boardgame_db(db, prepare_postprocessing: bool = True) -> None:
    """Load cached state if possible, otherwise rebuild the dataset and refresh caches."""
    print("\n------------------ Preparing BoardGameDB ------------------")

    file_count, file_hash = get_data_files_signature()
    manifest = load_cache_manifest(db.manifest_path)

    cache_valid = (
        manifest is not None
        and manifest.get("file_count") == file_count
        and manifest.get("file_hash") == file_hash
    )

    cached_state = load_cached_boardgame_state(db.cache_dir) if cache_valid else None
    if cached_state:
        db.df_games = cached_state["df_games"]
        db.unique_mechanics = cached_state["unique_mechanics"]
        db.unique_categories = cached_state["unique_categories"]
        db.unique_types = cached_state["unique_types"]
        db.unique_subdomains = cached_state["unique_subdomains"]
        db.unique_families = cached_state["unique_families"]
        db.mechanic_importances = cached_state["mechanic_importances"]
        db._niches_cache = cached_state["niches_cache"]
        print("\nLoaded from cache (data unchanged).")
    else:
        print("\nRebuilding dataset (data changed or cache missing).")
        db.load_data()

        db.cache_unique_mechanics()
        db.cache_unique_categories()
        db.cache_unique_types()
        db.cache_unique_subdomains()
        db.cache_and_convert_unique_wanted_families()

        db.load_property_mappings()
        db.collect_and_translate_properties()
        db.load_categorization_data_and_categorize_properties()

        save_cached_boardgame_state(db.cache_dir, {
            "df_games": db.df_games,
            "unique_mechanics": db.unique_mechanics,
            "unique_categories": db.unique_categories,
            "unique_types": db.unique_types,
            "unique_subdomains": db.unique_subdomains,
            "unique_families": db.unique_families,
            "mechanic_importances": db.mechanic_importances,
            "niches_cache": db._niches_cache,
        })
        save_cache_manifest(db.manifest_path, {"file_count": file_count, "file_hash": file_hash})

    db.init_search_engine()
    if prepare_postprocessing:
        db.cache_recommendations()

        try:
            db.create_and_persist_niches()
        except Exception:
            print("Warning: failed to compute/persist niches.")

    print("\n------------------------------------------------------------\n")