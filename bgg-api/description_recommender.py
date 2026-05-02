import re
import math
import html
from typing import Any, Iterable, Tuple, Dict, List
import pandas as pd


def _clean_html(raw_html: Any) -> str:
    if raw_html is None:
        return ""
    s = str(raw_html)
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _text_for_row(row: Any, fields: Iterable[str]) -> str:
    parts = []
    for f in fields:
        # support dict-like (pd.Series, dict) and generic objects
        if hasattr(row, 'get'):
            v = row.get(f, None)
        else:
            try:
                v = row[f]
            except Exception:
                v = None
        if v is None:
            continue
        if f == 'description':
            parts.append(_clean_html(v))
        else:
            parts.append(str(v))
    return " ".join(p for p in parts if p)


_TOKEN_RE = re.compile(r"\b[0-9a-zA-Z]{2,}\b")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower()
    return _TOKEN_RE.findall(text)


def _build_tfidf(docs: Iterable[str]) -> Tuple[Dict[str,int], List[Dict[str, float]], List[float]]:
    """Build a simple TF-IDF representation (pure Python).

    Returns (vocab, doc_tfidf_dicts, norms)
    - vocab: token -> doc frequency (used only for idf)
    - doc_tfidf_dicts: list of dict token->tfidf value per document
    - norms: list of vector norms for each document
    """
    docs_list = list(docs)
    N = len(docs_list)
    df_counts: Dict[str, int] = {}
    tokenized_docs: List[List[str]] = []
    for d in docs_list:
        toks = list(dict.fromkeys(_tokenize(d)))
        tokenized_docs.append(toks)
        for t in toks:
            df_counts[t] = df_counts.get(t, 0) + 1

    idf: Dict[str, float] = {}
    for t, cnt in df_counts.items():
        idf[t] = math.log((N + 1) / (cnt + 1)) + 1.0

    doc_tfidf: List[Dict[str, float]] = []
    norms: List[float] = []
    # Need full token counts per doc for TF
    for d, toks in zip(docs_list, tokenized_docs):
        full_toks = _tokenize(d)
        tf_counts: Dict[str, int] = {}
        for t in full_toks:
            tf_counts[t] = tf_counts.get(t, 0) + 1
        L = len(full_toks) if full_toks else 1
        vec: Dict[str, float] = {}
        norm_sq = 0.0
        for t, cnt in tf_counts.items():
            tf = cnt / L
            val = tf * idf.get(t, 0.0)
            vec[t] = val
            norm_sq += val * val
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 0.0
        doc_tfidf.append(vec)
        norms.append(norm)

    return df_counts, doc_tfidf, norms


def _cosine_sim(vec_a: Dict[str, float], vec_b: Dict[str, float], norm_a: float, norm_b: float) -> float:
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    # iterate over smaller dict
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    s = 0.0
    for k, v in vec_a.items():
        bv = vec_b.get(k)
        if bv is not None:
            s += v * bv
    return s / (norm_a * norm_b)


def recommend_by_description(game_id: Any, df: pd.DataFrame, k: int = 10,
                             text_fields: Tuple[str, str] = ('short_description', 'description')) -> pd.DataFrame:
    """Recommend games using only textual descriptions.

    - Combines `short_description` and cleaned `description` (HTML stripped).
    - Uses a small pure-Python TF-IDF implementation and cosine similarity.

    Args:
        game_id: id of the seed game (compared against `df['id']`).
        df: DataFrame containing at least `id`, `short_description`, `description`, `name`.
        k: number of recommendations to return.
        text_fields: tuple of (short_description_field, description_field).

    Returns:
        DataFrame of top-k candidates (columns preserved) with added `score` column.
    """
    seed_df = df[df['id'] == game_id]
    if seed_df.shape[0] == 0:
        raise ValueError(f"seed game id not found: {game_id}")
    seed = seed_df.iloc[0]

    # Build texts for all games
    texts = []
    ids = []
    for _, row in df.iterrows():
        ids.append(row.get('id'))
        texts.append(_text_for_row(row, text_fields))

    # Build TF-IDF
    _, doc_tfidf, norms = _build_tfidf(texts)

    # locate seed index
    try:
        seed_idx = ids.index(game_id)
    except ValueError:
        raise ValueError(f"seed game id not found in constructed list: {game_id}")

    seed_vec = doc_tfidf[seed_idx]
    seed_norm = norms[seed_idx]

    scores = []
    for i, (vec, norm) in enumerate(zip(doc_tfidf, norms)):
        if i == seed_idx:
            scores.append(0.0)
            continue
        sim = _cosine_sim(seed_vec, vec, seed_norm, norm)
        scores.append(sim)

    out = df.copy()
    out['score'] = scores
    return out.sort_values('score', ascending=False).head(k)


__all__ = ['recommend_by_description']
