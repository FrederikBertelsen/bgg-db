"""Hybrid recommender: embeddings (Sentence-Transformers or TF-IDF fallback)
plus tag-based weighted Jaccard; simple score normalization and merge.

Designed as a pragmatic, high-quality but small-code baseline:
- prefer `sentence-transformers` + `faiss` when available
- fallback to `sklearn` TF-IDF + NearestNeighbors
"""
from __future__ import annotations

import math
import html
import re
import time
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from recommender import load_or_compute_mechanic_importances, weighted_jaccard


_CLEAN_RE = re.compile(r"<[^>]+>")


def _clean_html(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw)
    s = html.unescape(s)
    s = _CLEAN_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _text_for_row(row: Any) -> str:
    parts: List[str] = []
    short = row.get('short_description') if hasattr(row, 'get') else row['short_description']
    desc = row.get('description') if hasattr(row, 'get') else row['description']
    if short:
        parts.append(str(short))
    if desc:
        parts.append(_clean_html(desc))
    return " ".join(parts).strip()


def _compute_embeddings(texts: List[str], model_name: str = 'all-MiniLM-L6-v2') -> Tuple[np.ndarray, str]:
    """Return (embeddings, method) where method is 'sbert' or 'tfidf'.
    Normalizes embeddings to unit length for cosine via inner product.
    """
    if SentenceTransformer is not None:
        model = SentenceTransformer(model_name)
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        # normalize
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms
        return embs.astype(np.float32), 'sbert'

    # fallback TF-IDF (dense path for simplicity/stability)
    tf = TfidfVectorizer(max_features=32768, ngram_range=(1,2), stop_words='english')
    X = tf.fit_transform(texts)
    # handle sparse matrix explicitly to satisfy type checkers
    try:
        import scipy.sparse as sp
    except Exception:
        sp = None

    if sp is not None and isinstance(X, sp.spmatrix):
        arr = X.toarray().astype(np.float32)
    else:
        arr = np.asarray(X, dtype=np.float32)

    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms
    return arr.astype(np.float32), 'tfidf'


def _nearest_scores_from_embeddings(embs: np.ndarray, seed_idx: int) -> np.ndarray:
    # emb rows already normalized -> inner product = cosine
    try:
        if faiss is not None:
            d = embs.shape[1]
            index = faiss.IndexFlatIP(d)
            index.add(embs)
            D, I = index.search(embs[[seed_idx]], embs.shape[0])
            scores = D[0]
            return scores
    except Exception:
        pass

    # sklearn fallback
    nbrs = NearestNeighbors(metric='cosine', algorithm='auto')
    nbrs.fit(embs)
    distances, indices = nbrs.kneighbors(embs[[seed_idx]], n_neighbors=embs.shape[0])
    # sklearn cosine distance in [0,2] for normalized vectors; convert to similarity
    sims = 1.0 - distances[0]
    return sims


def _minmax_scale(arr: np.ndarray) -> np.ndarray:
    if arr is None:
        return arr
    a = np.array(arr, dtype=float)
    mn = np.nanmin(a)
    mx = np.nanmax(a)
    if math.isclose(mx, mn):
        return np.zeros_like(a)
    return (a - mn) / (mx - mn)


def _ensure_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        return [x]
    try:
        return list(x)
    except Exception:
        return [x]


def recommend_hybrid(game_id: Any, df: pd.DataFrame, k: int = 10,
                     text_weight: float = 0.6, tag_weight: float = 0.3, rating_weight: float = 0.1,
                     model_name: str = 'all-MiniLM-L6-v2') -> pd.DataFrame:
    """Hybrid recommender combining text (embeddings) + tags + rating.

    Simple interface and minimal dependencies: will use SBERT+faiss when available,
    otherwise a robust TF-IDF + NearestNeighbors fallback.
    """
    seed_df = df[df['id'] == game_id]
    if seed_df.shape[0] == 0:
        raise ValueError(f"seed game id not found: {game_id}")
    seed_idx = int(df.index[df['id'] == game_id][0])

    # build texts
    texts = [ _text_for_row(row) for _, row in df.iterrows() ]

    embs, method = _compute_embeddings(texts, model_name=model_name)
    # ensure contiguous float32 array for faiss/sklearn
    embs = np.ascontiguousarray(np.asarray(embs, dtype=np.float32))
    emb_scores = _nearest_scores_from_embeddings(embs, seed_idx)
    # zero self-similarity
    emb_scores[seed_idx] = 0.0

    start_time =  time.perf_counter()
    # tag similarity using weighted_jaccard; use mechanic importances as weights for mechanics
    mech_weights = load_or_compute_mechanic_importances(df, path='data/mechanic_importances.csv')
    seed_row = seed_df.iloc[0]
    seed_mech = set(_ensure_list(seed_row.get('mechanics')))
    tag_scores = []
    for _, row in df.iterrows():
        other_mech = set(_ensure_list(row.get('mechanics')))
        tag_scores.append(float(weighted_jaccard(seed_mech, other_mech, mech_weights)))
    tag_scores = np.array(tag_scores, dtype=float)
    tag_scores[seed_idx] = 0.0

    # rating normalization
    ratings = np.array([
        (float(x) if (x is not None and x == x) else 0.0)
        for x in df.get('rating_average', pd.Series([0]*len(df)))
    ], dtype=float)
    ratings[seed_idx] = 0.0

    # scale each score to 0..1
    emb_s = _minmax_scale(emb_scores)
    tag_s = _minmax_scale(tag_scores)
    rating_s = _minmax_scale(ratings)

    final = (text_weight * emb_s) + (tag_weight * tag_s) + (rating_weight * rating_s)

    out = df.copy()
    out['score'] = final

    time_elapsed = time.perf_counter() - start_time
    print(f"(hybrid recommender: embedding method={method}, time={time_elapsed:.4f} seconds)")

    return out.sort_values('score', ascending=False).head(k)


__all__ = ['recommend_hybrid']
