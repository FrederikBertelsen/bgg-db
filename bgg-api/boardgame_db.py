import os
import glob
import re
import pandas as pd
import json
from collections import defaultdict
import pickle
import hashlib
from data_conversion import parse_json_like_columns
from recommender import _ensure_list, compute_mechanic_importances, recommend
from game_search import GameSearchEngine
from niche_detector import discover_niches


class BoardGameDB:
    def __init__(self):        
        self.df_games: pd.DataFrame = pd.DataFrame()
        self.unique_mechanics: set[str] = set()
        self.unique_categories: set[str] = set()
        
        # Search engine (initialized after df_games is loaded)
        self.search_engine: GameSearchEngine | None = None
        
        # Niches cache (lazy loaded)
        self._niches_cache = None
        
        # Mechanic importances cache
        self.mechanic_importances = None

        # Cache paths
        self.cache_dir = "data/cache"
        self.manifest_path = "data/cache_manifest.json"

        self.prepare_db()

    def _get_data_files_signature(self) -> tuple[int, str]:
        """Return (file_count, hash_of_sorted_filenames)."""
        data_folder_path = "data/final/"
        pattern = os.path.join(data_folder_path, "*.csv")
        files = sorted(glob.glob(pattern))
        
        if not files:
            return 0, ""
        
        filenames = [os.path.basename(f) for f in files]
        signature_str = ",".join(filenames)
        file_hash = hashlib.md5(signature_str.encode()).hexdigest()
        
        return len(files), file_hash

    def _load_cache_manifest(self) -> dict | None:
        """Load the cache manifest if it exists."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_cache_manifest(self, manifest: dict) -> None:
        """Save the cache manifest."""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f)

    def _load_cached_data(self) -> bool:
        """Load all cached data. Return True if successful, False otherwise."""
        try:
            with open(os.path.join(self.cache_dir, "df_games.pkl"), "rb") as f:
                self.df_games = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "unique_mechanics.pkl"), "rb") as f:
                self.unique_mechanics = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "unique_categories.pkl"), "rb") as f:
                self.unique_categories = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "unique_types.pkl"), "rb") as f:
                self.unique_types = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "unique_subdomains.pkl"), "rb") as f:
                self.unique_subdomains = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "unique_families.pkl"), "rb") as f:
                self.unique_families = pickle.load(f)
            
            with open(os.path.join(self.cache_dir, "mechanic_importances.pkl"), "rb") as f:
                self.mechanic_importances = pickle.load(f)

            # load niches cache if present
            with open(os.path.join(self.cache_dir, "niches.pkl"), "rb") as f:
                self._niches_cache = pickle.load(f)
            
            return True
        except Exception:
            return False

    def _save_cached_data(self) -> None:
        """Save all cached data."""
        os.makedirs(self.cache_dir, exist_ok=True)
        
        with open(os.path.join(self.cache_dir, "df_games.pkl"), "wb") as f:
            pickle.dump(self.df_games, f)
        
        with open(os.path.join(self.cache_dir, "unique_mechanics.pkl"), "wb") as f:
            pickle.dump(self.unique_mechanics, f)
        
        with open(os.path.join(self.cache_dir, "unique_categories.pkl"), "wb") as f:
            pickle.dump(self.unique_categories, f)
        
        with open(os.path.join(self.cache_dir, "unique_types.pkl"), "wb") as f:
            pickle.dump(self.unique_types, f)
        
        with open(os.path.join(self.cache_dir, "unique_subdomains.pkl"), "wb") as f:
            pickle.dump(self.unique_subdomains, f)
        
        with open(os.path.join(self.cache_dir, "unique_families.pkl"), "wb") as f:
            pickle.dump(self.unique_families, f)
        
        with open(os.path.join(self.cache_dir, "mechanic_importances.pkl"), "wb") as f:
            pickle.dump(self.mechanic_importances, f)

        # save niches cache if available
        with open(os.path.join(self.cache_dir, "niches.pkl"), "wb") as f:
            pickle.dump(self._niches_cache, f)

    def get_game_by_id(self, id: str) -> pd.Series | None:
        """
        Return a dict of the board game with the given `id`, or `None` if not found.
        """
        row = self.df_games[self.df_games["id"] == id]
        if row.empty:
            return None
        return row.iloc[0]

    def get_games_by_ids(self, ids: list[str]) -> pd.DataFrame | None:
        """
        Return a list of dicts for the board games with the given `ids`. If an `id`
        is not found, it is skipped (not included in the result).
        """
        if not ids:
            return None

        # Preserve the order of `ids` as provided by the caller.
        # Using `reindex` on `id` index returns rows in the same order
        # and inserts NaN rows for missing ids which we then drop.
        ids = [str(i) for i in ids]
        rows = self.df_games.set_index("id").reindex(ids).dropna(how="all").reset_index()

        if rows.empty:
            return None

        return rows
    
    def get_game_by_name(self, name: str) -> pd.Series | None:
        """
        Return a dict of the board game with the given `name` (or alternate name), or `None` if not found.
        Delegates to search engine.
        """
        if self.search_engine is None:
            return None
        return self.search_engine.get_game_by_name(name)

    def get_games_by_names(self, names: list[str]) -> pd.DataFrame | None:
        """
        Return a list of dicts for the board games with the given `names` (or alternate names). If a `name`
        is not found, it is skipped (not included in the result). Delegates to search engine.
        """
        if self.search_engine is None:
            return None
        return self.search_engine.get_games_by_names(names)

    def get_english_names_deduplicated(self, names: list[str]) -> list[str]:
        """
        Return the English names for a given list of `names` (which may be alternate names).
        Delegates to search engine.
        """
        if self.search_engine is None:
            return []
        return self.search_engine.get_english_names_deduplicated(names)



    def search_games(self, searchTerm: str, n: int = 5, threshold: int = 70) -> pd.DataFrame | None:
        """
        Return a list of dicts for board games whose `name` or `alternate_names` fuzzy-match the given `searchTerm`.
        Delegates to search engine.
        """
        if self.search_engine is None:
            return None
        return self.search_engine.search_games(searchTerm, n=n, threshold=threshold)

    
    def autocomplete_search(self, searchTerm: str, n: int = 5, threshold: int = 60) -> list[tuple[str, int]]:
        """Return up to `n` matches as (name, score). Delegates to search engine."""
        if self.search_engine is None:
            return []
        return self.search_engine.autocomplete_search(searchTerm, n=n, threshold=threshold)

    def recommend_games(self, id: str, n: int = 5) -> pd.DataFrame | None:
        """
        Return a list of up to `n` dicts for board games recommended based on the
        game with the given `id`. Recommendations are determined by the `recommended`
        column, which contains comma-separated `id`s of recommended games. If the
        given `id` is not found or has no recommendations, an empty list is returned.
        """

        game = self.get_game_by_id(id)

        if game is None or game.empty:
            return None
        
        recommendations = recommend(id, self.df_games, k=n, print_results=False)

        return recommendations
    
    def init_search_engine(self) -> None:
        """Initialize the search engine for game name lookups."""
        if self.df_games.empty:
            return
        print("\nInitializing search engine...")
        self.search_engine = GameSearchEngine(self.df_games)
    
    def get_niches(self, verbose: bool = True, params: dict | None = None) -> list:
        """
        Discover board game niches from the current dataset.
        
        Args:
            verbose: Print progress messages
            params: Optional dict of tunable parameters (merged with defaults)
            
        Returns:
            List of niches, each as tuple:
                (cluster_set, niche_props_dict, selected_props_list, qualifying_games_list)
        """
        if self.df_games.empty:
            return []
        
        # Use cache if available
        if self._niches_cache is not None:
            return self._niches_cache
        
        if verbose:
            print("\nDiscovering board game niches...")
        
        niches = discover_niches(self.df_games, params=params, verbose=verbose)
        
        # Cache for future calls
        self._niches_cache = niches
        
        return niches

    def create_and_persist_niches(self, niche_csv_path: str = "data/niches.csv", verbose: bool = True, params: dict | None = None, save_cache: bool = True) -> None:
        """
        Compute niches (using discover_niches), persist them to a CSV and add
        `niches` (list of niche_ids) to `self.df_games` so the dataset knows which
        niches each game qualifies for.

        The CSV columns are: `niche_id`, `name`, `description`, `properties`, `games_count`.
        `name` and `description` are left empty for manual editing later.
        `properties` is stored as a JSON array string.
        """
        if self.df_games.empty:
            if verbose:
                print("No games loaded; skipping niche creation.")
            return

        # Ensure niches are computed and cached by get_niches
        niches = self.get_niches(verbose=verbose, params=params)

        os.makedirs(os.path.dirname(niche_csv_path), exist_ok=True)

        niche_rows = []
        game_to_niches = defaultdict(list)

        for i, niche in enumerate(niches):
            cluster_set, niche_props, selected, qualifying_games = niche
            niche_id = f"niche_{i+1}"
            properties = selected if selected is not None else []
            games_list = [gid for gid, _, _, _ in qualifying_games]

            for gid in games_list:
                game_to_niches[gid].append(niche_id)

            niche_rows.append({
                "niche_id": niche_id,
                "name": "",
                "description": "",
                "properties": json.dumps(properties, ensure_ascii=False),
                "games_count": len(games_list),
            })

        niches_df = pd.DataFrame(niche_rows, columns=["niche_id", "name", "description", "properties", "games_count"])
        niches_df.to_csv(niche_csv_path, index=False)

        # Attach niche ids to df_games as a list column `niches`
        # Preserve existing values if column exists by merging
        def _assign_niches(gid):
            return game_to_niches.get(str(gid), [])

        self.df_games["niches"] = self.df_games["id"].apply(_assign_niches)

        if save_cache:
            # Persist updated df_games (and other cached artifacts)
            try:
                self._save_cached_data()
            except Exception:
                if verbose:
                    print("Warning: failed to save cache after persisting niches.")
    
    def cache_all_names(self) -> None:
        """Initialize search engine (renamed from cache_all_names)."""
        self.init_search_engine()

    def cache_unique_mechanics(self) -> None:
        """
        Precompute and cache the unique mechanics across all games in the dataset.
        This can speed up recommendation computations that rely on mechanic similarity.
        """

        print("\nCaching unique mechanics...")

        self.unique_mechanics = set()
        for mechanics in self.df_games['mechanics'].dropna():
            self.unique_mechanics.update(_ensure_list(mechanics))

        # create dataframe and save to .csv file
        unique_mechanics_df = pd.DataFrame(list(self.unique_mechanics), columns=['mechanic'])
        unique_mechanics_df.sort_values(by='mechanic', inplace=True)
        # unique_mechanics_df.to_csv('data/unique_mechanics.csv', index=False)

    def cache_unique_categories(self) -> None:
        """
        Precompute and cache the unique categories across all games in the dataset.
        This can speed up recommendation computations that rely on category similarity.
        """

        print("\nCaching unique categories...")

        self.unique_categories = set()
        for categories in self.df_games['categories'].dropna():
            self.unique_categories.update(_ensure_list(categories))

        # create dataframe and save to .csv file
        unique_categories_df = pd.DataFrame(list(self.unique_categories), columns=['category'])
        unique_categories_df.sort_values(by='category', inplace=True)
        # unique_categories_df.to_csv('data/unique_categories.csv', index=False)

    def cache_recommendations(self):
        print("\nPrecomputing mechanic importances...")
        self.mechanic_importances = compute_mechanic_importances(self.df_games)

    def cache_unique_types(self) -> None:
        """
        Precompute and cache the unique types across all games in the dataset.
        This can speed up recommendation computations that rely on type similarity.
        """

        print("\nCaching unique types...")

        self.unique_types = set()
        for types in self.df_games['types'].dropna():
            self.unique_types.update(_ensure_list(types))

        # create dataframe and save to .csv file
        unique_types_df = pd.DataFrame(list(self.unique_types), columns=['type'])
        unique_types_df.sort_values(by='type', inplace=True)
        # unique_types_df.to_csv('data/unique_types.csv', index=False)

    def cache_unique_subdomains(self) -> None:
        """
        Precompute and cache the unique subdomains across all games in the dataset.
        This can speed up recommendation computations that rely on subdomain similarity.
        """

        print("\nCaching unique subdomains...")

        self.unique_subdomains = set()
        for subdomains in self.df_games['subdomains'].dropna():
            self.unique_subdomains.update(_ensure_list(subdomains))

        # create dataframe and save to .csv file
        unique_subdomains_df = pd.DataFrame(list(self.unique_subdomains), columns=['subdomain'])
        unique_subdomains_df.sort_values(by='subdomain', inplace=True)
        # unique_subdomains_df.to_csv('data/unique_subdomains.csv', index=False)

    def cache_and_convert_unique_wanted_families(self) -> None:
        """
        Precompute and cache the unique families across all games in the dataset.
        This can speed up recommendation computations that rely on family similarity.
        """
        wanted_families = {
            "animals": "Animals",
            "Safari Parks": "Animals",
            "zoos": "Animals",
            "Aquaria": "Animals",

            "adventure": "Adventure",

            "Creatures": "Creatures",

            "Crowdfunding": "Crowdfunded",

            "Digital Implementation": "Digital Implementation",

            "vehicles": "Vehicles",
            "automotive": "Vehicles",
            "cars": "Vehicles",
            "airline": "Vehicles",
            "Trains": "Vehicles",
            "Trucks": "Vehicles",

            "Tropical": "Nature",
            "Nature": "Nature",
            "trees": "Nature",
            "wildlife": "Nature",
            "Forest": "Nature",
            "Weather": "Nature",
            "Swamps": "Nature",
            "bogs": "Nature",
            "Wetlands": "Nature",

            "Witches": "Magic",
            "magic": "Magic",
            "Wizards": "Magic",
            "Spells": "Magic",
            "Sorcery": "Magic",

            "disney": "Fairy Tales",
            "Folk Tales & Fairy Tales": "Fairy Tales",
            "Storytelling": "Fairy Tales",

            "Tableau Building": "Tableau Building",

            "Food": "Food",
            "Restaurant": "Food",
            "Café": "Food",
            "cafe": "Food",

            "ocean": "Ocean",
            "Under the Sea": "Ocean",
            "sea": "Ocean",

            "history": "History",
            "History": "History",
            "Vikings": "History",

            "card game": "Card Game",
            "Playing Card": "Card Game",

            "simulation": "Simulation",

            "crossword": "Word Game",
            "Word Games": "Word Game",
            "words": "Word Game",

            "dungeon Crawler": "Dungeon Crawler",

            "escape Room": "Escape Room",

            "two-player": "Two-Player",
            "Two Player": "Two-Player",

            "fighting": "Fighting",

            "cities": "Location",
            "City": "Location",
            "Continent": "Location",
            "Country": "Location",
            "ancient": "Location",
            "Islands": "Location",
            "Mountains": "Location",
            "Region": "Location",
            "Rivers": "Location",
            "States:": "Location",
            
            "Sports": "Sports",

            "Space": "Science Fiction",
            "Cyberpunk": "Science Fiction",
            "Robots": "Science Fiction",
            "Sci-Fi": "Science Fiction",
            "Steampunk": "Science Fiction",

            "Spooky": "Horror",
            "Horror": "Horror",
            "scary": "Horror",

            "Mythology": "Mythology",
            "Religious": "Mythology",
            "Cryptids": "Mythology",
            "Cthulhu": "Mythology",

            "Pirates": "Ocean",
            "Sealife": "Ocean",

            "Post-Apocalyptic": "Post-Apocalyptic",

            "4X": "4X",

            "Bluffing": "Bluffing",

            "Campaign": "Campaign",

            "Trading Game": "Trading",
            "trading": "Trading",

            "Medical": "Science",
            "doctors": "Science",
            "Scientist": "Science",
            "Biology": "Science",
            "science": "Science",

            "Crime": "Crime",
            "burglary": "Crime",
            "Heist": "Crime",

            "Detective": "Murder / Mystery",

            "Cooperative": "Cooperative",

            "Hidden Movement": "Hidden Movement",

            "Deckbuilding": "Deckbuilding",

            "Roll-and-Write": "Roll-and-Write",
            "roll and write": "Roll-and-Write",

            "Construction": "Construction",

            "collectible": "Collectible",

            "grid": "Grid",

            "Hex": "Hexagonal",

            "Polyominoes": "Polyominoes",

            "Timer": "Timer",

            "Meeples": "Meeples",
            "Standees": "Meeples",

            "Miniature": "Miniatures",
            
            "3d": "3D",
            "3 dimensional": "3D",
            "3-dimensional": "3D",

            "dice": "Dice",
            "Drop Tower": "Dice",
            
            "War games": "War Game",
            "war game": "War Game",
            "war-game": "War Game",
            "war ": "War Game",
            "war-": "War Game",
            "warfare": "War Game",

            "drawing": "Drawing",
            "Crayons": "Drawing",
            "Dry Erase Markers": "Drawing",

            "Digital Hybrid": "Digital Hybrid",

            "Trivia": "Trivia",
            "Quiz": "Trivia",
        }

        pre_remove_contains = ["Hall of Fame"]

        print("\nCaching and converting unique families...")

        # filter families based on wanted_families mapping (if value contains key from wanted_families, keep it and translate to the mapped value; otherwise discard) and remove families that contain any of the pre_remove_contains substrings (case-insensitive)
        # each games list of families should not have duplicates after this filtering, but we can keep track of the unique families across all games in a set for caching and later use in recommendations. We can also save the unique families to a .csv file for reference.
        self.df_games['families'] = self.df_games['families'].apply(lambda fams: [family for family in _ensure_list(fams) if not any(substring.lower() in family.lower() for substring in pre_remove_contains)] if fams is not None else fams)
        self.df_games['families'] = self.df_games['families'].apply(lambda fams: list(set(wanted_families[key] for family in _ensure_list(fams) for key in wanted_families if key.lower() in family.lower())) if fams is not None else fams)

        self.unique_families = set()
        for families in self.df_games['families'].dropna():
            self.unique_families.update(_ensure_list(families))

        # create dataframe and save to .csv file
        unique_families_df = pd.DataFrame(list(self.unique_families), columns=['family'])
        unique_families_df.sort_values(by='family', inplace=True)
        # add a count of how many games have each family as a new column
        unique_families_df['count'] = unique_families_df['family'].apply(lambda f: self.df_games['families'].dropna().apply(lambda fams: f in _ensure_list(fams)).sum())
        # unique_families_df.to_csv('data/unique_families.csv', index=False)


    def load_property_mappings(self) -> None:
        # check if data/property_mappings.csv exists and load it if so, otherwise create an empty mapping
        # check if all types, mechanics, and categories in the dataset are present in the mapping, and add the missing ones and save the updated mapping back to the CSV file
        # the columns are: 'property', 'type'
        # use unique values from cache.
        mapping_file = 'data/property_metadata/property_mappings.csv'
        if os.path.exists(mapping_file):
            self.property_mappings = pd.read_csv(mapping_file)
            # ensure 'name' is loaded as a list of strings (if it is not a string representation of a list, convert it to a list; if it is NaN, convert to empty list)
            self.property_mappings['name'] = self.property_mappings['name'].apply(lambda x: _ensure_list(x) if pd.notna(x) else [])
        else:
            self.property_mappings = pd.DataFrame(columns=['property', 'name'])

        existing_properties = set(self.property_mappings['property'])
        all_properties = set()
        for prop_set in [self.unique_mechanics, self.unique_categories, self.unique_types, self.unique_families, self.unique_subdomains]:
            all_properties.update(prop_set)
        
        missing_properties = all_properties - existing_properties
        if missing_properties:
            print(f"\nAdding {len(missing_properties)} missing properties to mapping...")
            new_rows = pd.DataFrame({
                'property': list(missing_properties), 
                'name': [None] * len(missing_properties), 
            })
            self.property_mappings = pd.concat([self.property_mappings, new_rows], ignore_index=True)
            # sort before saving
            # self.property_mappings.sort_values(by='property', inplace=True)
            self.property_mappings.to_csv(mapping_file, index=False)
        
        self.property_mappings.set_index('property', inplace=True)

    def collect_and_translate_properties(self) -> None:
        # collect all unique mechanics, categories, types, and families from the dataset and translate them to a common language using the property_mappings (if a mapping exists for a given property, use the mapped name; otherwise keep the original name)
        # this can be used to create a more unified representation of game properties for recommendation computations
        def translate_property(prop: str) -> list[str]:
            if prop in self.property_mappings.index:
                name = self.property_mappings.loc[prop, 'name']
                if isinstance(name, str) and len(name) > 0:
                    return [name]
                if isinstance(name, list) and len(name) > 0:
                    return name
            return [prop]

        # collect all to single list column of unique properties for mechanics, categories, types, and families
        # translate_property(prop) returns a list -> flatten and deduplicate
        self.df_games['properties'] = self.df_games.apply(
            lambda row: list(
                set(
                    name
                    for prop in (
                        _ensure_list(row['mechanics'])
                        + _ensure_list(row['categories'])
                        + _ensure_list(row['types'])
                        + _ensure_list(row['families'])
                    )
                    if pd.notna(prop)
                    for name in translate_property(prop)
                )
            ),
            axis=1,
        )


    def load_categorization_data_and_categorize_properties(self) -> None:
        # nearly same as load_property_mappings(), but load data/property_metadata/property_categorizations.csv which has columns 'property' and 'category', and use it to categorize properties into broader categories (e.g., 'worker placement' mechanic might be categorized under 'mechanic' category, while 'Fantasy' family might be categorized under 'theme' category).
        # This can help with recommendation computations that want to consider properties at different levels of granularity.

        categorization_file = 'data/property_metadata/property_categorizations.csv'
        if os.path.exists(categorization_file):
            self.property_categorizations = pd.read_csv(categorization_file)
        else:
            self.property_categorizations = pd.DataFrame(columns=['property', 'category'])

        existing_properties = set(self.property_categorizations['property'])
        all_properties = set()
        # use properties column
        for props in self.df_games['properties'].dropna():
            all_properties.update(props)

        
        missing_properties = all_properties - existing_properties
        if missing_properties:
            print(f"\nAdding {len(missing_properties)} missing properties to categorization...")
            new_rows = pd.DataFrame({
                'property': list(missing_properties), 
                'category': [None] * len(missing_properties), 
            })
            self.property_categorizations = pd.concat([self.property_categorizations, new_rows], ignore_index=True)
            # sort before saving
            # self.property_categorizations.sort_values(by='property', inplace=True)
            self.property_categorizations.to_csv(categorization_file, index=False)
        
        self.property_categorizations.set_index('property', inplace=True)
        
        # convert properties to dict of categories to list of properties
        # use only the properties and the property categories. the unique lists on this class are NOT the same as the p_ columns. so DON'T USE self.unique_mechanics, etc.
        def _categorize_properties(props, category):
            if props is None or props is pd.NA:
                return []
            if isinstance(props, float) and pd.isna(props):
                return []
            if not isinstance(props, (list, tuple, set, pd.Index)):
                return []
            return [
                prop for prop in props
                if prop in self.property_categorizations.index and self.property_categorizations.loc[prop, 'category'] == category
            ]

        self.df_games['p_mechanics'] = self.df_games['properties'].apply(lambda props: _categorize_properties(props, 'Mechanic'))
        self.df_games['p_types'] = self.df_games['properties'].apply(lambda props: _categorize_properties(props, 'Type'))
        self.df_games['p_components'] = self.df_games['properties'].apply(lambda props: _categorize_properties(props, 'Component'))
        self.df_games['p_themes'] = self.df_games['properties'].apply(lambda props: _categorize_properties(props, 'Theme'))
        self.df_games['p_tags'] = self.df_games['properties'].apply(lambda props: _categorize_properties(props, 'Tag'))


    def load_data(self) -> None:
        """
        Load CSVs from `data/final/` in filename order (oldest -> newest).
        The first file is treated as the full dataset; subsequent files are
        updates that overwrite older values by `id` (keeps older values where
        an update doesn't provide a value). Returns a combined DataFrame
        with `id` as a regular column.
        """
        data_folder_path = "data/final/"
        pattern = os.path.join(data_folder_path, "*.csv")
        files = sorted(glob.glob(pattern))

        if not files:
            raise ValueError(f"No CSV files found in {data_folder_path}")

        print("\nLoading Data:")

        # Load base (oldest) file
        base = pd.read_csv(files[0])
        base = parse_json_like_columns(base)
        if "id" not in base.columns:
            raise ValueError(f"CSV file {files[0]} does not contain required 'id' column")
        base["id"] = base["id"].astype(str)
        base = base.drop_duplicates(subset="id", keep="last").set_index("id")
        print(f"    Base dataset: {len(base)}   - '{files[0]}'")

        # Apply updates in filename order so newer files overwrite older values.
        for f in files[1:]:
            upd = pd.read_csv(f)
            upd = parse_json_like_columns(upd)
            if "id" not in upd.columns:
                raise ValueError(f"CSV file {f} does not contain required 'id' column")
            upd["id"] = upd["id"].astype(str)
            upd = upd.drop_duplicates(subset="id", keep="last").set_index("id")
            # prefer values from the update where present, otherwise keep existing
            base = upd.combine_first(base)
            print(f"    Applied update: {len(upd)}   -> {len(base)} - '{f}'")

        self.df_games = base.reset_index()
    
    def prepare_db(self):
        print("\n------------------ Preparing BoardGameDB ------------------")

        # Check if cache is valid
        file_count, file_hash = self._get_data_files_signature()
        manifest = self._load_cache_manifest()
        
        cache_valid = (
            manifest is not None
            and manifest.get("file_count") == file_count
            and manifest.get("file_hash") == file_hash
        )

        if cache_valid and self._load_cached_data():
            print("\nLoaded from cache (data unchanged).")
        else:
            print("\nRebuilding dataset (data changed or cache missing).")
            self.load_data()
                    
            self.cache_unique_mechanics()
            self.cache_unique_categories()
            self.cache_unique_types()
            self.cache_unique_subdomains()
            self.cache_and_convert_unique_wanted_families()

            self.load_property_mappings()
            self.collect_and_translate_properties()
            self.load_categorization_data_and_categorize_properties()

            # Save cache
            self._save_cached_data()
            self._save_cache_manifest({"file_count": file_count, "file_hash": file_hash})

        self.init_search_engine()
        self.cache_recommendations()
        # Compute and persist niches, and attach niche ids to games
        try:
            self.create_and_persist_niches()
        except Exception:
            print("Warning: failed to compute/persist niches.")

        print("\n------------------------------------------------------------\n")