

import os
import math
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
        for key in ("averageweight", "average_weight", "averageWeight", "weight"):
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
        mechs = set(_ensure_list(row.get('mechanics')))
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


def recommend(game_id: Any, df: pd.DataFrame, method: str = 'simple', k: int = 10, weights: dict | None = None, print_results: bool = False) -> pd.DataFrame:
    """Basic recommender: Jaccard on `categories` and `mechanics` plus numeric similarity on `average_rating` and `weight`.

    Args:
        game_id: id of the seed game (compared against `df['id']`).
        df: dataframe with game details.
        method: reserved (only 'simple' supported now).
        k: number of results to return.
        weights: dict with keys `cat`, `mech`, `rating`, `weight` controlling contribution.
        print_results: whether to print the recommended games.

    Returns:
        DataFrame of top-k candidates with a `score` column.
    """
    if weights is None:
        weights = {"cat": 0.3, "mech": 0.4, "rating": 0.2, "weight": 0.1}
    # treat `types` the same as `categories` by default
    if 'types' not in weights:
        weights['types'] = weights.get('cat', 0)

    seed_df = df[df['id'] == game_id]
    if seed_df.shape[0] == 0:
        raise ValueError(f"seed game id not found: {game_id}")
    seed = seed_df.iloc[0]

    cands = df[df['id'] != game_id].copy()

    seed_cats = set(_ensure_list(seed.get('categories', [])))
    seed_types = set(_ensure_list(seed.get('types', [])))
    seed_mech = set(_ensure_list(seed.get('mechanics', [])))
    seed_weight = _extract_weight(seed.get('weight', None)) or seed.get('average_weight')

    # categories, types and mechanics similarity (0..1)
    cats_sim = cands['categories'].apply(lambda x: jaccard(set(_ensure_list(x)), seed_cats))
    # types similarity (same treatment as categories)
    if 'types' in cands.columns:
        types_sim = cands['types'].apply(lambda x: jaccard(set(_ensure_list(x)), seed_types))
    else:
        types_sim = pd.Series(0.0, index=cands.index)

    # mechanics similarity: use weighted Jaccard with precomputed mechanic importances
    mech_weights = load_or_compute_mechanic_importances(df, path='data/mechanic_importances.csv')
    mech_sim = cands['mechanics'].apply(lambda x: weighted_jaccard(seed_mech, set(_ensure_list(x)), mech_weights))

    # rating bonus: higher-rated games receive a small global quality bonus (avg_rating/10)
    def rating_bonus(x):
        try:
            r = float(x)
            return max(0.0, min(1.0, r / 10.0))
        except Exception:
            return 0.0

    rating_sim_series = cands['average_rating'].apply(rating_bonus)

    # weight similarity: assume typical boardgame weight range ~ [1,5]
    def weight_sim(x):
        w = _extract_weight(x) or (x if isinstance(x, (int, float)) else None)
        if seed_weight is None or w is None:
            return 0.0
        return max(0.0, 1.0 - (abs(w - float(seed_weight)) / 4.0))

    weight_sim_series = cands['weight'].apply(weight_sim)

    score = (
        weights.get('cat', 0) * cats_sim
        + weights.get('types', 0) * types_sim
        + weights.get('mech', 0) * mech_sim
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
            overall_rank = next((r.get('rank') for r in (row.get('ranks') or []) if r.get('category') == 'Overall Rank'), None)
            rows.append({
                'name': row.get('name', ''),
                'score': f"{row.get('score', 0):.3f}",
                'overall_rank': overall_rank or '',
                'avg_rating': row.get('average_rating') or '',
                'weight': _extract_weight(row.get('weight')) or row.get('average_weight') or '',
                'year': row.get('year_published') or '',
                'url': f"https://boardgamegeek.com/boardgame/{row.get('id')}"
            })

        disp = pd.DataFrame(rows)
        with pd.option_context('display.max_colwidth', 60):
            print(disp.to_string(index=False))
    return out.sort_values('score', ascending=False).head(k)
