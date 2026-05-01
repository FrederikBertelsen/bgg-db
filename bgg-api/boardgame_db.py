import os
import glob
import pandas as pd
import re
from thefuzz import process, fuzz
from recommender import _ensure_list, compute_mechanic_importances, recommend

# Common stopwords to ignore for token-based matching/penalties
STOPWORDS = {
    "of",
    "the",
    "a",
    "an",
    "and",
    "in",
    "on",
    "for",
    "to",
    "with",
    "from",
    "by",
    "at",
    "is",
    "it",
    "its",
    "as",
    "or",
    "that",
    "this",
}


class BoardGameDB:
    def __init__(self):        
        self.df_games: pd.DataFrame = pd.DataFrame()
        self.name_to_id: dict[str, str] = {}
        self.name_is_canonical: set[str] = set()
        self.unique_mechanics: set[str] = set()
        self.unique_categories: set[str] = set()

        # Tunable search weights and penalties. Adjust these in one place.
        self.search_weights: dict[str, int] = {
            # substring match (primary)
            "substr_base": 80,
            "substr_start_bonus": 35,
            "substr_full_term_start_bonus": 35,
            "substr_position_bonus_max": 20,
            "substr_position_penalty_per_token": 3,
            "full_word_bonus": 30,
            # token overlap match (secondary)
            "token_base": 60,
            "token_start_bonus": 20,
            "token_position_bonus_max": 12,
            "token_position_penalty_per_token": 2,
            # penalties
            "alternate_name_penalty": 25,
            "short_token_length": 3,
            "short_token_penalty": 15,
            "very_short_name_len": 3,
            "very_short_name_penalty": 75,
            # fallback settings
            "fallback_limit_multiplier": 4,
            # minimum alternate-name length to cache
            "min_alt_name_length": 3,
        }

        self.prepare_db()

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
        Uses a precomputed mapping of names to ids for fast lookup.
        """
        game_id = self.name_to_id.get(name)
        if game_id is None:
            return None
        return self.get_game_by_id(game_id)

    def get_games_by_names(self, names: list[str]) -> pd.DataFrame | None:
        """
        Return a list of dicts for the board games with the given `names` (or alternate names). If a `name`
        is not found, it is skipped (not included in the result). Uses a precomputed mapping of names to ids for fast lookup.
        """
        game_ids: list[str] = []
        for name in names:
            gid = self.name_to_id.get(name)
            if gid is not None:
                game_ids.append(gid)

        # Preserve order and remove duplicates while keeping first occurrence
        if not game_ids:
            return None

        game_ids = list(dict.fromkeys(game_ids))

        return self.get_games_by_ids(game_ids)

    def get_english_names_deduplicated(self, names: list[str]) -> list[str]:
        """
        Return the English names for a given list of `names` (which may be alternate names), or `None` if not found.
        Uses a precomputed mapping of names to ids and then looks up the English names by id.
        """
        game_ids = list(set(self.name_to_id.get(name) for name in names if self.name_to_id.get(name) is not None))

        english_names = self.df_games[self.df_games["id"].isin(game_ids)]["name"].dropna().unique().tolist()

        return english_names



    def search_games(self, searchTerm: str, n: int = 5, threshold: int = 70) -> pd.DataFrame | None:
        """
        Return a list of dicts for board games whose `name` or `alternate_names` fuzzy-match the given `searchTerm`.
        Uses RapidFuzz for fast approximate matching; returns results with a score >= 60 (0-100).
        """
        matches = self.autocomplete_search(searchTerm, n=n, threshold=threshold)

        if not matches:
            return None

        # matches is a list of (name, score)
        names = [m for m, _ in matches]
        
        df_matches = self.get_games_by_names(names)
        if df_matches is None:
            return None

        df_matches['score'] = [s for _, s in matches]
        
        return df_matches

    
    def autocomplete_search(self, searchTerm: str, n: int = 5, threshold: int = 60) -> list[tuple[str, int]]:
        """Return up to `n` matches as (name, score).

        Algorithm (simple, deterministic):
        - normalize input and candidate names (lower, strip punctuation/extra whitespace)
        - primary pass: keep names where normalized `searchTerm` is a substring of normalized name
        - secondary pass: token-substring match (all search tokens appear inside some name token)
        - fallback: use fuzzy scorer (`token_set_ratio`) if no primary/secondary hits
        Scoring is simple: earlier position and full-word/start matches increase score; alternate names are penalized.
        """
        if not searchTerm:
            return []

        def normalize(s: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()

        st = normalize(searchTerm)
        if not st:
            return []
        st_tokens = [t for t in st.split() if t]

        names = getattr(self, "search_names", list(self.name_to_id.keys()))

        # Fast path for very short search terms (3 or fewer characters):
        # 1) Find candidate names whose normalized form startswith the term
        # 2) Sort candidate names alphabetically
        # 3) Map names -> ids, dedupe ids while preserving order
        # 4) Fetch games for only the top `n` ids and return their canonical
        #    English names (with a uniform score)
        if len(searchTerm.strip()) <= 3:
            # collect candidate original names that match the prefix
            candidate_names: list[str] = []
            for name in names:
                if normalize(name).startswith(st):
                    candidate_names.append(name)

            if not candidate_names:
                return []

            # sort candidate names alphabetically (case-insensitive)
            candidate_names.sort(key=lambda s: normalize(s))

            # map sorted names -> ids, dedupe ids preserving first occurrence
            seen_ids: set[str] = set()
            ordered_ids: list[str] = []
            for nm in candidate_names:
                gid = self.name_to_id.get(nm)
                if not gid:
                    continue
                if gid in seen_ids:
                    continue
                seen_ids.add(gid)
                ordered_ids.append(gid)
                if len(ordered_ids) >= n:
                    break

            if not ordered_ids:
                return []

            # fetch games in the ordered id sequence
            results: list[tuple[str, int]] = []
            for gid in ordered_ids:
                game = self.get_game_by_id(gid)
                if game is None:
                    continue
                results.append((game["name"], 100))

            return results

        def compute_score(orig_name: str) -> int | None:
            norm_name = normalize(orig_name)
            if not norm_name:
                return None
            # Perfect-match short-circuit: identical normalized name -> maximal score
            if norm_name == st:
                return 9999
            name_tokens = [t for t in norm_name.split() if t]
            is_canonical = orig_name in getattr(self, "name_is_canonical", set())
            # quick checks and collect matched tokens
            w = self.search_weights

            # Prepare token lists and stopword-filtered tokens
            st_tokens_raw = [t for t in st.split() if t]
            st_tokens_filtered = [t for t in st_tokens_raw if t not in STOPWORDS]
            st_tokens_used = st_tokens_filtered if st_tokens_filtered else st_tokens_raw

            matched_tokens: list[str] = []

            # Primary: substring match (allow phrase spanning multiple tokens)
            if st in norm_name:
                # Build token spans so we can map substring char index -> token index
                token_spans = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", norm_name)]
                ch_index = norm_name.find(st)
                substring_end = ch_index + len(st)
                token_pos = None
                for i, (tok, start, end) in enumerate(token_spans):
                    if start <= ch_index < end:
                        token_pos = i
                        break

                # matched tokens are those tokens which overlap the substring span
                matched_tokens = [tok for tok, start, end in token_spans if start < substring_end and end > ch_index]

                score = w["substr_base"]
                if token_pos == 0:
                    score += w["substr_start_bonus"]
                # bonus when the whole search term appears at the start of the name
                if norm_name.startswith(st):
                    score += w.get("substr_full_term_start_bonus", 0)
                if token_pos is not None:
                    score += max(0, w["substr_position_bonus_max"] - token_pos * w["substr_position_penalty_per_token"])
                if any(st == tok for tok in name_tokens):
                    score += w["full_word_bonus"]
            else:
                # Secondary: token-substring match using filtered tokens (ignore stopwords)
                if not st_tokens_used:
                    return None
                if all(any(tok in nt for nt in name_tokens) for tok in st_tokens_used):
                    matched_tokens = [nt for nt in name_tokens if any(tok in nt for tok in st_tokens_used)]
                    earliest = None
                    for i, nt in enumerate(name_tokens):
                        if any(tok in nt for tok in st_tokens_used):
                            earliest = i
                            break
                    score = w["token_base"]
                    if earliest == 0:
                        score += w["token_start_bonus"]
                    if earliest is not None:
                        score += max(0, w["token_position_bonus_max"] - earliest * w["token_position_penalty_per_token"])
                else:
                    return None

            # penalize alternate names (they're noisy)
            if not is_canonical:
                score -= w["alternate_name_penalty"]

            # Short-token handling: base on search tokens (not only matched token lengths)
            short_token_penalty_amount = 0
            search_short_tokens = [tok for tok in st_tokens_raw if len(tok) <= w["short_token_length"] and tok not in STOPWORDS]
            if search_short_tokens:
                for s_tok in search_short_tokens:
                    if any(s_tok == nt for nt in name_tokens):
                        # exact short-token match is acceptable
                        continue
                    elif any(s_tok in nt for nt in name_tokens):
                        # short query token only appears as substring -> harsher penalty
                        short_token_penalty_amount = max(short_token_penalty_amount, w["short_token_penalty"] * 2)
            else:
                # if any matched token itself is very short, penalize (fallback)
                if matched_tokens and any(len(mt) <= w["short_token_length"] for mt in matched_tokens):
                    short_token_penalty_amount = max(short_token_penalty_amount, w["short_token_penalty"])

            # also penalize if the whole normalized name is extremely short and not an exact match
            if len(norm_name.replace(" ", "")) <= w["very_short_name_len"] and norm_name != st:
                short_token_penalty_amount = max(short_token_penalty_amount, w["very_short_name_penalty"])

            score -= short_token_penalty_amount
            # Return raw (unclamped) integer score so aggregation can use full range.
            return int(score)

        def _search_prefix_match(orig_name: str) -> bool:
            """Return True if the search term tokens match the start of `orig_name` tokens (token-prefix)."""
            norm_n = normalize(orig_name)
            name_toks = [t for t in norm_n.split() if t]
            st_toks_raw = [t for t in st.split() if t]
            if not name_toks or not st_toks_raw:
                return False
            if len(st_toks_raw) > len(name_toks):
                return False
            for i, tok in enumerate(st_toks_raw):
                if not name_toks[i].startswith(tok):
                    return False
            return True

        candidates: list[tuple[str, int, bool]] = []

        # primary + secondary pass
        for name in names:
            sc = compute_score(name)
            if sc is not None and sc >= threshold:
                starts = _search_prefix_match(name)
                candidates.append((name, sc, starts))

        # fallback to fuzzy scoring if no candidates
        if not candidates:
            w = self.search_weights
            results = process.extract(searchTerm, names, scorer=fuzz.token_set_ratio, processor=str.lower, limit=n * w["fallback_limit_multiplier"])
            for choice, fscore in results:
                if fscore < threshold:
                    continue
                is_canonical = choice in getattr(self, "name_is_canonical", set())
                norm_choice = normalize(choice)
                # Perfect-match short-circuit for fallback choices
                if norm_choice == st:
                    starts = True
                    candidates.append((choice, 9999, starts))
                    continue
                name_tokens = [t for t in norm_choice.split() if t]

                # stopword-filtered tokens for fallback
                st_tokens_filtered = [t for t in st_tokens if t not in STOPWORDS]
                st_tokens_used = st_tokens_filtered if st_tokens_filtered else st_tokens

                # determine matched tokens for the fallback choice (handle phrase spans)
                if st in norm_choice:
                    token_spans = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", norm_choice)]
                    ch_index = norm_choice.find(st)
                    substring_end = ch_index + len(st)
                    matched_tokens_fb = [tok for tok, start, end in token_spans if start < substring_end and end > ch_index]
                else:
                    matched_tokens_fb = [nt for nt in name_tokens if any(tok in nt for tok in st_tokens_used)]

                adj = int(fscore) - (w["alternate_name_penalty"] if not is_canonical else 0)

                # short-token logic for fallback (based on search tokens)
                search_short_tokens = [tok for tok in st_tokens if len(tok) <= w["short_token_length"] and tok not in STOPWORDS]
                if search_short_tokens:
                    for s_tok in search_short_tokens:
                        if any(s_tok == nt for nt in name_tokens):
                            continue
                        elif any(s_tok in nt for nt in name_tokens):
                            adj -= w["short_token_penalty"] * 2
                else:
                    if matched_tokens_fb and any(len(mt) <= w["short_token_length"] for mt in matched_tokens_fb):
                        adj -= w["short_token_penalty"]

                if len(norm_choice.replace(' ', '')) <= w["very_short_name_len"] and norm_choice != st:
                    adj -= w["very_short_name_penalty"]

                # Keep raw adj for aggregation; convert to int when appending.
                starts = _search_prefix_match(choice)
                candidates.append((choice, int(adj), starts))

        if not candidates:
            return []

        # aggregate by canonical English name (keep highest score per canonical game)
        # store (score, starts_with_flag) and prefer starts_with when scores tie
        best_by_game: dict[str, tuple[int, bool]] = {}
        for name, score, starts in candidates:
            gid = self.name_to_id.get(name)
            if not gid:
                continue
            game = self.get_game_by_id(gid)
            if game is None:
                continue
            eng = game["name"]
            existing = best_by_game.get(eng)
            if existing is None:
                best_by_game[eng] = (score, starts)
            else:
                ex_score, ex_starts = existing
                if score > ex_score or (score == ex_score and starts and not ex_starts):
                    best_by_game[eng] = (score, starts)

        # sort by score then by starts_with flag (both desc)
        ordered_items = sorted(best_by_game.items(), key=lambda kv: (kv[1][0], kv[1][1]), reverse=True)[:n]
        # return same shape as before: list of (name, score)
        # Return raw (non-clamped) scores so large debugging bonuses are visible.
        # Keep lower bound at 0 to avoid negative display values.
        ordered = [(eng, max(0, int(score_starts[0]))) for eng, score_starts in ordered_items]
        return ordered

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

        return recommendations.sort_values('score', ascending=False)
    
    def cache_all_names(self) -> None:
        """
        Precompute and cache a mapping of game `name` and `alternate_names` to `id` for all games in a dataset.
        This can speed up searches by name for the main search function.
        """

        print("\nCaching all game names...")

        name_to_id = {}
        name_is_canonical = set()
        for _, row in self.df_games.iterrows():
            # canonical English name
            name_to_id[row['name']] = row['id']
            name_is_canonical.add(row['name'])
            # alternate names
            if pd.notnull(row['alternate_names']):
                for alt_name in _ensure_list(row['alternate_names']):
                    alt_clean = alt_name.strip()
                    # skip very short alternate names which are noisy (e.g., 'Ion')
                    if len(alt_clean) < self.search_weights.get("min_alt_name_length", 3):
                        continue
                    # only add if not already present (keep first mapping)
                    name_to_id[alt_clean] = row['id']

        self.name_to_id = name_to_id
        self.name_is_canonical = name_is_canonical
        # cache a list of names to use for fast fuzzy searching
        self.search_names = list(name_to_id.keys())

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
        unique_mechanics_df.to_csv('data/unique_mechanics.csv', index=False)

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
        unique_categories_df.to_csv('data/unique_categories.csv', index=False)

    def compute_recommendations(self):
        print("\nPrecomputing mechanic importances...")
        compute_mechanic_importances(self.df_games)

    def load_data(self) -> None:
        """
        Load CSVs from `data/final/` in filename order (oldest → newest).
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
        if "id" not in base.columns:
            raise ValueError(f"CSV file {files[0]} does not contain required 'id' column")
        base["id"] = base["id"].astype(str)
        base = base.drop_duplicates(subset="id", keep="last").set_index("id")
        print(f"    Base dataset: {len(base)}   - '{files[0]}'")

        # Apply updates in filename order so newer files overwrite older values.
        for f in files[1:]:
            upd = pd.read_csv(f)
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

        self.load_data()
        self.compute_recommendations()
        self.cache_unique_mechanics()
        self.cache_unique_categories()
        self.cache_all_names()

        print("\n------------------------------------------------------------\n")