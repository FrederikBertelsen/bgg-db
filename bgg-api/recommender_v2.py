import os
import math
import ast
import pandas as pd
from typing import Any


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni > 0 else 0.0


def _ensure_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    # sometimes stored as a single string
    if isinstance(x, str):
        try:
            parsed = ast.literal_eval(x)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [x]
    try:
        return list(x)
    except Exception:
        return []


def _extract_weight(w: Any) -> float | None:
    # handle cases where weight is a dict with averageweight key
    if w is None:
        return None
    if isinstance(w, (int, float)):
        return float(w)
    if isinstance(w, dict):
        for key in ("weight_average", "averageweight", "average_weight", "averageWeight", "weight"):
            if key in w:
                try:
                    return float(w[key])
                except Exception:
                    continue
    return None


def compute_mechanic_importances(df: pd.DataFrame, out_csv: str = 'data/mechanic_importances.csv', method: str = 'idf') -> pd.DataFrame:
    """Compute a global importance score per mechanic and save to CSV.

    - method 'idf' (default): importance = log((N+1)/(df_count+1)) then normalized to 0..1.
    The CSV columns: mechanic,count,idf,weight
    Returns the DataFrame written.
    """
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    N = int(len(df))
    counts: dict[str, int] = {}
    for _, row in df.iterrows():
        mechs = set(_ensure_list(row.get('p_mechanics')))
        for m in mechs:
            counts[m] = counts.get(m, 0) + 1

    records = []
    for mech, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        if method == 'idf':
            idf = math.log((N + 1) / (cnt + 1))
        else:
            # fallback to inverse popularity
            idf = math.log((N + 1) / (cnt + 1))
        records.append({'mechanic': mech, 'count': int(cnt), 'idf': float(idf)})

    dfw = pd.DataFrame.from_records(records)
    if dfw.shape[0] == 0:
        # empty result, write empty file and return
        dfw.to_csv(out_csv, index=False)
        return dfw

    # normalize idf to 0..1 for weight
    max_idf = dfw['idf'].max()
    if max_idf <= 0:
        dfw['weight'] = 0.0
    else:
        dfw['weight'] = (dfw['idf'] / max_idf).astype(float)

    dfw.to_csv(out_csv, index=False)
    return dfw


def load_or_compute_mechanic_importances(df: pd.DataFrame, path: str = 'data/mechanic_importances.csv') -> dict:
    """Load mechanic importances from CSV if present, otherwise compute and save.

    Returns a dict: {mechanic: weight}
    """
    try:
        if os.path.isfile(path):
            dfw = pd.read_csv(path)
            if 'mechanic' in dfw.columns and 'weight' in dfw.columns:
                return dict(zip(dfw['mechanic'].astype(str), dfw['weight'].astype(float)))
    except Exception:
        # fallthrough to compute
        pass

    dfw = compute_mechanic_importances(df, out_csv=path, method='idf')
    if 'mechanic' in dfw.columns and 'weight' in dfw.columns:
        return dict(zip(dfw['mechanic'].astype(str), dfw['weight'].astype(float)))
    return {}


def weighted_jaccard(a: set, b: set, weights: dict, default_weight: float = 1e-6) -> float:
    """Weighted Jaccard similarity between sets a and b using per-token weights."""
    if not a and not b:
        return 0.0
    inter = a & b
    uni = a | b
    sum_inter = 0.0
    sum_uni = 0.0
    for m in inter:
        sum_inter += float(weights.get(m, default_weight))
    for m in uni:
        sum_uni += float(weights.get(m, default_weight))
    if sum_uni <= 0.0:
        return 0.0
    return sum_inter / sum_uni


def _resolve_game(game: Any, df: pd.DataFrame | None = None, game_id_map: dict | None = None) -> Any:
    """Resolve a game id or row-like object into something with .get access.
    
    Args:
        game: game id, pd.Series, or dict
        df: DataFrame (fallback for lookup if game_id_map not provided)
        game_id_map: optional dict mapping game_id -> row for O(1) lookup
    """
    if isinstance(game, pd.Series):
        return game
    if isinstance(game, dict):
        return game
    
    # Fast path: use pre-built mapping
    if game_id_map is not None and game in game_id_map:
        return game_id_map[game]
    
    # Fallback: use dataframe lookup
    if df is None:
        raise ValueError("df is required when passing game ids")

    seed_df = df[df['id'] == game]
    if seed_df.shape[0] == 0:
        raise ValueError(f"game id not found: {game}")
    return seed_df.iloc[0]


def score_connection(
    game_a: Any,
    game_b: Any,
    df: pd.DataFrame | None = None,
    weights: dict | None = None,
    mech_weights: dict | None = None,
    game_id_map: dict | None = None,
) -> dict:
    """Return a symmetric connection score between two games.

    The score reuses the same property-family comparisons as the recommender,
    but compares two games directly instead of comparing a seed against a
    candidate pool.
    
    Args:
        game_a, game_b: game ids or row-like objects
        df: DataFrame (fallback)
        weights: property weights
        mech_weights: mechanic importance weights
        game_id_map: optional dict mapping game_id -> row for O(1) lookup (recommended for performance)
    """
    if weights is None:
        weights = {"types": 0.3, "mech": 0.35, "comp": 0.2, "themes": 0.1, "rating": 0.0, "weight": 0.05}

    a = _resolve_game(game_a, df, game_id_map=game_id_map)
    b = _resolve_game(game_b, df, game_id_map=game_id_map)

    if mech_weights is None and df is not None:
        mech_weights = load_or_compute_mechanic_importances(df, path='data/mechanic_importances.csv')
    elif mech_weights is None:
        mech_weights = {}

    a_types = set(_ensure_list(a.get('p_types', [])))
    b_types = set(_ensure_list(b.get('p_types', [])))
    a_mech = set(_ensure_list(a.get('p_mechanics', [])))
    b_mech = set(_ensure_list(b.get('p_mechanics', [])))
    a_comp = set(_ensure_list(a.get('p_components', [])))
    b_comp = set(_ensure_list(b.get('p_components', [])))
    a_themes = set(_ensure_list(a.get('p_themes', [])))
    b_themes = set(_ensure_list(b.get('p_themes', [])))

    types_sim = jaccard(a_types, b_types)
    mech_sim = weighted_jaccard(a_mech, b_mech, mech_weights)
    comp_sim = jaccard(a_comp, b_comp)
    themes_sim = jaccard(a_themes, b_themes)

    def rating_similarity(x: Any, y: Any) -> float:
        try:
            ax = float(x)
            ay = float(y)
            return max(0.0, 1.0 - (abs(ax - ay) / 10.0))
        except Exception:
            return 0.0

    def weight_similarity(x: Any, y: Any) -> float:
        ax = _extract_weight(x) or (x if isinstance(x, (int, float)) else None)
        ay = _extract_weight(y) or (y if isinstance(y, (int, float)) else None)
        if ax is None or ay is None:
            return 0.0
        return max(0.0, 1.0 - (abs(float(ax) - float(ay)) / 4.0))

    rating_sim = rating_similarity(a.get('rating_average'), b.get('rating_average'))
    weight_sim = weight_similarity(a.get('weight_average'), b.get('weight_average'))

    score = (
        weights.get('types', 0.0) * types_sim
        + weights.get('mech', 0.0) * mech_sim
        + weights.get('comp', 0.0) * comp_sim
        + weights.get('themes', 0.0) * themes_sim
        + weights.get('rating', 0.0) * rating_sim
        + weights.get('weight', 0.0) * weight_sim
    )

    return {
        'score': float(score),
        'types': float(types_sim),
        'mechanics': float(mech_sim),
        'components': float(comp_sim),
        'themes': float(themes_sim),
        'rating': float(rating_sim),
        'weight': float(weight_sim),
        'game_a_id': a.get('id'),
        'game_b_id': b.get('id'),
        'game_a_name': a.get('name'),
        'game_b_name': b.get('name'),
    }


def recommend(game_id: Any, df: pd.DataFrame, method: str = 'simple', k: int = 10, weights: dict | None = None, print_results: bool = False) -> pd.DataFrame:
    """Recommender using p_ columns: p_types, p_mechanics, p_components, p_themes.
    
    Each property type gets its own weight for fine-grained control.

    Args:
        game_id: id of the seed game (compared against `df['id']`).
        df: dataframe with game details.
        method: reserved (only 'simple' supported now).
        k: number of results to return.
        weights: dict with keys `types`, `mech`, `comp`, `themes`, `rating`, `weight` controlling contribution.
        print_results: whether to print the recommended games.

    Returns:
        DataFrame of top-k candidates with a `score` column.
    """
    if weights is None:
        weights = {"types": 0.3, "mech": 0.25, "comp": 0.25, "themes": 0.0, "rating": 0.1, "weight": 0.1}

    seed_df = df[df['id'] == game_id]
    if seed_df.shape[0] == 0:
        raise ValueError(f"seed game id not found: {game_id}")
    seed = seed_df.iloc[0]

    cands = df[df['id'] != game_id].copy()

    seed_types = set(_ensure_list(seed.get('p_types', [])))
    seed_mech = set(_ensure_list(seed.get('p_mechanics', [])))
    seed_comp = set(_ensure_list(seed.get('p_components', [])))
    seed_themes = set(_ensure_list(seed.get('p_themes', [])))
    seed_weight = _extract_weight(seed.get('weight_average', None)) or seed.get('weight_average')

    # types similarity (0..1)
    types_sim = cands['p_types'].apply(lambda x: jaccard(set(_ensure_list(x)), seed_types))
    
    # mechanics similarity: use weighted Jaccard with precomputed mechanic importances
    mech_weights = load_or_compute_mechanic_importances(df, path='data/mechanic_importances.csv')
    mech_sim = cands['p_mechanics'].apply(lambda x: weighted_jaccard(seed_mech, set(_ensure_list(x)), mech_weights))
    
    # components similarity (0..1)
    comp_sim = cands['p_components'].apply(lambda x: jaccard(set(_ensure_list(x)), seed_comp))
    
    # themes similarity (0..1)
    themes_sim = cands['p_themes'].apply(lambda x: jaccard(set(_ensure_list(x)), seed_themes))

    # rating bonus: higher-rated games receive a small global quality bonus (avg_rating/10)
    def rating_bonus(x):
        try:
            r = float(x)
            return max(0.0, min(1.0, r / 10.0))
        except Exception:
            return 0.0

    rating_sim_series = cands['rating_average'].apply(rating_bonus)

    # weight similarity: assume typical boardgame weight range ~ [1,5]
    def weight_sim(x):
        w = _extract_weight(x) or (x if isinstance(x, (int, float)) else None)
        if seed_weight is None or w is None:
            return 0.0
        return max(0.0, 1.0 - (abs(w - float(seed_weight)) / 4.0))

    weight_sim_series = cands['weight_average'].apply(weight_sim)

    score = (
        weights.get('types', 0) * types_sim
        + weights.get('mech', 0) * mech_sim
        + weights.get('comp', 0) * comp_sim
        + weights.get('themes', 0) * themes_sim
        + weights.get('rating', 0) * rating_sim_series
        + weights.get('weight', 0) * weight_sim_series
    )

    out = cands.copy()
    out['score'] = score

    if print_results:
        print(f"Recommendations for '{seed['name']}' (id={game_id}):")
        results = out.sort_values('score', ascending=False).head(k).copy()
        rows = []
        for _, row in results.iterrows():
            overall_rank = next((r.get('rank') for r in (row.get('ranks') or []) if r.get('category') == 'Overall'), None)
            rows.append({
                'name': row.get('name', ''),
                'score': f"{row.get('score', 0):.3f}",
                'overall_rank': overall_rank or '',
                'avg_rating': row.get('rating_average') or '',
                'weight': _extract_weight(row.get('weight_average')) or row.get('weight_average') or '',
                'year': row.get('year_published') or '',
                'url': f"https://boardgamegeek.com/boardgame/{row.get('id')}"
            })

        disp = pd.DataFrame(rows)
        with pd.option_context('display.max_colwidth', 60):
            print(disp.to_string(index=False))
    return out.sort_values('score', ascending=False).head(k)
