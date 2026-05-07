import pandas as pd
from recommender import compute_mechanic_importances, recommend
from game_search import GameSearchEngine
from niche_detector import discover_niches
from boardgame_db_properties import (
    collect_and_translate_properties,
    load_or_create_property_categorizations,
    load_or_create_property_mappings,
    normalize_families,
)
from boardgame_db_features import collect_unique_values
from boardgame_db_io import load_merged_data,save_cached_boardgame_state
from boardgame_db_niches import build_niche_name_cache, create_and_persist_niches
from boardgame_db_pipeline import prepare_boardgame_db


class BoardGameDB:
    def __init__(self, prepare_postprocessing: bool = True):        
        self.df_games: pd.DataFrame = pd.DataFrame()
        self.unique_mechanics: set[str] = set()
        self.unique_categories: set[str] = set()
        
        # Search engine (initialized after df_games is loaded)
        self.search_engine: GameSearchEngine | None = None
        
        # Niches cache (lazy loaded)
        self._niches_cache = None
        self._niche_name_cache: dict[str, dict] | None = None
        
        # Mechanic importances cache
        self.mechanic_importances = None

        # Cache paths
        self.cache_dir = "data/cache"
        self.manifest_path = "data/cache_manifest.json"

        self.prepare_db(prepare_postprocessing=prepare_postprocessing)

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

    def get_niche_by_name(self, niche_name: str) -> pd.Series | None:
        """
        Return a Series for the niche with the given `niche_name`, or `None` if not found.

        Uses an in-memory cache so repeated lookups are O(1) and avoid re-reading
        `data/niches.csv` on each request.
        """
        self._ensure_niche_name_cache()
        if self._niche_name_cache is None:
            return None

        niche = self._niche_name_cache.get(niche_name)
        if niche is None:
            return None
        return pd.Series(niche)

    def _ensure_niche_name_cache(self, niche_csv_path: str = "data/niches.csv") -> None:
        """Build niche-name cache once: name -> metadata + games list."""
        if self._niche_name_cache is not None:
            return
        self._niche_name_cache = build_niche_name_cache(self.df_games, niche_csv_path=niche_csv_path)

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
        Return a list of dicts for board games whose `name` or `alternative_names` fuzzy-match the given `searchTerm`.
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
        if self.df_games.empty:
            if verbose:
                print("No games loaded; skipping niche creation.")
            return

        # Ensure niches are computed and cached by get_niches
        niches = self.get_niches(verbose=verbose, params=params)

        self.df_games = create_and_persist_niches(self.df_games, niches, niche_csv_path=niche_csv_path)
        # Invalidate and rebuild niche-name cache after persistence updates.
        self._niche_name_cache = None
        self._ensure_niche_name_cache(niche_csv_path=niche_csv_path)

        if save_cache:
            # Persist updated df_games (and other cached artifacts)
            try:
                save_cached_boardgame_state(self.cache_dir, {
                    "df_games": self.df_games,
                    "unique_mechanics": self.unique_mechanics,
                    "unique_categories": self.unique_categories,
                    "unique_types": self.unique_types,
                    "unique_subdomains": self.unique_subdomains,
                    "unique_families": self.unique_families,
                    "mechanic_importances": self.mechanic_importances,
                    "niches_cache": self._niches_cache,
                })
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
        self.unique_mechanics = collect_unique_values(self.df_games, 'mechanics')

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
        self.unique_categories = collect_unique_values(self.df_games, 'categories')

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
        self.unique_types = collect_unique_values(self.df_games, 'types')

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
        self.unique_subdomains = collect_unique_values(self.df_games, 'subdomains')

        # create dataframe and save to .csv file
        unique_subdomains_df = pd.DataFrame(list(self.unique_subdomains), columns=['subdomain'])
        unique_subdomains_df.sort_values(by='subdomain', inplace=True)
        # unique_subdomains_df.to_csv('data/unique_subdomains.csv', index=False)

    def cache_and_convert_unique_wanted_families(self) -> None:
        """Normalize family names and cache the resulting unique values."""
        self.unique_families = normalize_families(self.df_games)


    def load_property_mappings(self) -> None:
        self.property_mappings = load_or_create_property_mappings(
            self.unique_mechanics,
            self.unique_categories,
            self.unique_types,
            self.unique_families,
            self.unique_subdomains,
        )

    def collect_and_translate_properties(self) -> None:
        collect_and_translate_properties(self.df_games, self.property_mappings)


    def load_categorization_data_and_categorize_properties(self) -> None:
        self.property_categorizations = load_or_create_property_categorizations(self.df_games)


    def load_data(self) -> None:
        self.df_games = load_merged_data()
    
    def prepare_db(self, prepare_postprocessing: bool = True):
        prepare_boardgame_db(self, prepare_postprocessing=prepare_postprocessing)