import ast
import html
import json
import math
import os
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


DEFAULT_CACHE_DIR = "data/recommender"
DEFAULT_ARTIFACT_FILE = "artifacts.pkl"
DEFAULT_META_FILE = "meta.json"

STRUCTURED_BLOCKS: dict[str, str] = {
    "mechanics": "p_mechanics",
    "types": "p_types",
    "components": "p_components",
    "themes": "p_themes",
}

DEFAULT_BLOCK_WEIGHTS: dict[str, float] = {
    "mechanics": 0.40,
    "types": 0.20,
    "components": 0.20,
    "themes": 0.05,
    "text": 0.10,
}

DEFAULT_RATING_WEIGHT = 0.05
DEFAULT_WEIGHT_PENALTY_STRENGTH = 0.30
DEFAULT_WEIGHT_PENALTY_MAX_GAP = 2.5


_ARTIFACT_MEMORY_CACHE: dict[tuple[str, str], "RecommenderArtifacts"] = {}


@dataclass
class RecommenderArtifacts:
    ids: list[str]
    id_to_index: dict[str, int]
    block_matrices: dict[str, sparse.csr_matrix]
    rating_bonus: np.ndarray
    weight_values: np.ndarray
    cache_key: str


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
    if w is None:
        return None
    if isinstance(w, (int, float)):
        if math.isnan(float(w)):
            return None
        return float(w)
    if isinstance(w, dict):
        for key in ("weight_average", "averageweight", "average_weight", "averageWeight", "weight"):
            if key in w:
                try:
                    parsed = float(w[key])
                    if math.isnan(parsed):
                        continue
                    return parsed
                except Exception:
                    continue
    return None


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        value = float(x)
        if math.isnan(value):
            return default
        return value
    except Exception:
        return default


def _clean_text(raw: Any) -> str:
    if raw is None:
        return ""
    txt = str(raw)
    if not txt:
        return ""
    txt = html.unescape(txt)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _tokens_from_value(value: Any) -> list[str]:
    tokens: list[str] = []
    for token in _ensure_list(value):
        if token is None:
            continue
        token_str = str(token).strip()
        if token_str:
            tokens.append(token_str)
    return list(set(tokens))


def _canonicalize_for_cache(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _canonicalize_for_cache(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set, pd.Index)):
        items = [_canonicalize_for_cache(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return str(value)


def _stable_cache_string(value: Any) -> str:
    canonical = _canonicalize_for_cache(value)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)


def _compute_cache_key(df: pd.DataFrame) -> str:
    if "id" not in df.columns:
        return "missing-id"
    key_columns = [
        "id",
        "p_mechanics",
        "p_types",
        "p_components",
        "p_themes",
        "short_description",
        "description",
        "rating_average",
        "weight_average",
    ]
    available_columns = [col for col in key_columns if col in df.columns]
    if not available_columns:
        ids = df["id"].astype(str).sort_values(ignore_index=True)
        id_hash = int(pd.util.hash_pandas_object(ids, index=False).sum())
        return f"{len(ids)}:{id_hash}"

    key_df = df[available_columns].copy()
    for col in available_columns:
        key_df[col] = key_df[col].map(_stable_cache_string)

    data_hash = int(pd.util.hash_pandas_object(key_df, index=False).sum())
    return f"{len(key_df)}:{data_hash}"


def _build_structured_matrix(series: pd.Series) -> sparse.csr_matrix:
    docs = [_tokens_from_value(value) for value in series]
    n_rows = len(docs)
    if n_rows == 0:
        return sparse.csr_matrix((0, 0), dtype=np.float32)

    df_counter: Counter[str] = Counter()
    for doc_tokens in docs:
        for token in set(doc_tokens):
            df_counter[token] += 1

    if not df_counter:
        return sparse.csr_matrix((n_rows, 0), dtype=np.float32)

    vocab = {token: idx for idx, token in enumerate(sorted(df_counter.keys()))}
    n_docs = float(n_rows)

    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for row_idx, doc_tokens in enumerate(docs):
        for token in doc_tokens:
            col_idx = vocab[token]
            idf = math.log((n_docs + 1.0) / (df_counter[token] + 1.0)) + 1.0
            rows.append(row_idx)
            cols.append(col_idx)
            data.append(float(idf))

    matrix = sparse.csr_matrix((data, (rows, cols)), shape=(n_rows, len(vocab)), dtype=np.float32)
    return normalize(matrix, norm="l2", axis=1)


def _build_text_matrix(df: pd.DataFrame) -> sparse.csr_matrix:
    short_series = df.get("short_description", pd.Series([""] * len(df), index=df.index))
    long_series = df.get("description", pd.Series([""] * len(df), index=df.index))

    corpus = [
        f"{_clean_text(short_text)} {_clean_text(long_text)}".strip()
        for short_text, long_text in zip(short_series, long_series)
    ]

    if not any(corpus):
        return sparse.csr_matrix((len(df), 0), dtype=np.float32)

    vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode", min_df=2, ngram_range=(1, 2))
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return sparse.csr_matrix((len(df), 0), dtype=np.float32)
    return normalize(matrix, norm="l2", axis=1)


def _build_rating_bonus(df: pd.DataFrame) -> np.ndarray:
    ratings = df.get("rating_average", pd.Series([0.0] * len(df), index=df.index)).apply(_safe_float)
    return np.clip((ratings.to_numpy(dtype=np.float32) / 10.0), 0.0, 1.0)


def _build_weight_values(df: pd.DataFrame) -> np.ndarray:
    values: list[float] = []
    if "weight_average" in df.columns:
        src_series = df["weight_average"]
    else:
        src_series = pd.Series([np.nan] * len(df), index=df.index)

    for value in src_series:
        parsed = _extract_weight(value)
        values.append(float(parsed) if parsed is not None else np.nan)

    return np.array(values, dtype=np.float32)


def _build_artifacts(df: pd.DataFrame, cache_key: str) -> RecommenderArtifacts:
    ids = df["id"].astype(str).tolist()
    id_to_index = {game_id: idx for idx, game_id in enumerate(ids)}

    block_matrices: dict[str, sparse.csr_matrix] = {}
    for block_name, column_name in STRUCTURED_BLOCKS.items():
        if column_name in df.columns:
            block_matrices[block_name] = _build_structured_matrix(df[column_name])
        else:
            block_matrices[block_name] = sparse.csr_matrix((len(df), 0), dtype=np.float32)

    block_matrices["text"] = _build_text_matrix(df)

    return RecommenderArtifacts(
        ids=ids,
        id_to_index=id_to_index,
        block_matrices=block_matrices,
        rating_bonus=_build_rating_bonus(df),
        weight_values=_build_weight_values(df),
        cache_key=cache_key,
    )


def build_recommender_artifacts(
    df: pd.DataFrame,
    cache_dir: str = DEFAULT_CACHE_DIR,
    force_rebuild: bool = False,
) -> RecommenderArtifacts:
    os.makedirs(cache_dir, exist_ok=True)
    artifact_path = os.path.join(cache_dir, DEFAULT_ARTIFACT_FILE)
    meta_path = os.path.join(cache_dir, DEFAULT_META_FILE)

    cache_key = _compute_cache_key(df)
    memory_key = (cache_dir, cache_key)

    if not force_rebuild:
        cached = _ARTIFACT_MEMORY_CACHE.get(memory_key)
        if cached is not None:
            return cached

    if not force_rebuild and os.path.exists(artifact_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("cache_key") == cache_key:
                with open(artifact_path, "rb") as f:
                    loaded = pickle.load(f)
                if isinstance(loaded, RecommenderArtifacts):
                    _ARTIFACT_MEMORY_CACHE[memory_key] = loaded
                    return loaded
        except Exception:
            pass

    artifacts = _build_artifacts(df=df, cache_key=cache_key)

    with open(artifact_path, "wb") as f:
        pickle.dump(artifacts, f)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"cache_key": cache_key}, f)

    _ARTIFACT_MEMORY_CACHE[memory_key] = artifacts

    return artifacts


def _resolve_block_weights(weights: dict | None) -> dict[str, float]:
    resolved = dict(DEFAULT_BLOCK_WEIGHTS)
    if not weights:
        return resolved

    legacy_key_mapping = {
        "cat": "themes",
        "mech": "mechanics",
        "type": "types",
        "comp": "components",
    }

    for raw_key, value in weights.items():
        key = legacy_key_mapping.get(raw_key, raw_key)
        if key in resolved:
            resolved[key] = _safe_float(value, resolved[key])

    return resolved


def _weight_penalty_vector(
    weight_values: np.ndarray,
    seed_weight: float | None,
    strength: float,
    max_gap: float,
) -> np.ndarray:
    if seed_weight is None:
        return np.ones_like(weight_values, dtype=np.float32)

    penalties = np.ones_like(weight_values, dtype=np.float32)
    valid = ~np.isnan(weight_values)
    if not np.any(valid):
        return penalties

    gaps = np.abs(weight_values[valid] - np.float32(seed_weight))
    normalized_gaps = np.clip(gaps / np.float32(max_gap), 0.0, 1.0)
    penalties[valid] = 1.0 - np.float32(strength) * normalized_gaps
    return penalties


def compute_mechanic_importances(
    df: pd.DataFrame,
    out_csv: str = "data/mechanic_importances.csv",
    method: str = "idf",
) -> pd.DataFrame:
    """Backward-compatible helper kept for existing callers.

    This computes mechanic-only IDF weights and writes them to CSV.
    The main recommender now uses `build_recommender_artifacts`.
    """
    _ = method
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    n_docs = int(len(df))
    counts: dict[str, int] = {}
    for mechanics in df.get("p_mechanics", df.get("mechanics", pd.Series([], dtype=object))):
        for token in set(_tokens_from_value(mechanics)):
            counts[token] = counts.get(token, 0) + 1

    records: list[dict[str, float | int | str]] = []
    for mechanic, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        idf = math.log((n_docs + 1) / (count + 1)) + 1.0
        records.append({"mechanic": mechanic, "count": int(count), "idf": float(idf)})

    out = pd.DataFrame.from_records(records)
    if out.empty:
        out.to_csv(out_csv, index=False)
        return out

    max_idf = float(out["idf"].max())
    out["weight"] = out["idf"].apply(lambda x: float(x / max_idf) if max_idf > 0 else 0.0)
    out.to_csv(out_csv, index=False)
    return out


def recommend(
    game_id: Any,
    df: pd.DataFrame,
    method: str = "sparse",
    k: int = 10,
    weights: dict | None = None,
    print_results: bool = False,
    artifacts: RecommenderArtifacts | None = None,
) -> pd.DataFrame:
    """Recommend top-k similar games using cached sparse feature blocks.

    Scoring:
    - weighted cosine similarity on `p_mechanics`, `p_types`, `p_components`, `p_themes`, and text
    - small additive rating bonus
    - post-score soft penalty for large weight/complexity gaps
    """
    _ = method

    game_id_str = str(game_id)
    if artifacts is None:
        artifacts = build_recommender_artifacts(df)
    assert artifacts is not None

    seed_idx = artifacts.id_to_index.get(game_id_str)
    if seed_idx is None:
        raise ValueError(f"seed game id not found: {game_id_str}")

    block_weights = _resolve_block_weights(weights)
    rating_weight = _safe_float((weights or {}).get("rating_bonus", DEFAULT_RATING_WEIGHT), DEFAULT_RATING_WEIGHT)
    weight_penalty_strength = _safe_float(
        (weights or {}).get("weight_penalty_strength", DEFAULT_WEIGHT_PENALTY_STRENGTH),
        DEFAULT_WEIGHT_PENALTY_STRENGTH,
    )
    weight_penalty_max_gap = _safe_float(
        (weights or {}).get("weight_penalty_max_gap", DEFAULT_WEIGHT_PENALTY_MAX_GAP),
        DEFAULT_WEIGHT_PENALTY_MAX_GAP,
    )

    n_rows = len(df)
    base_score = np.zeros(n_rows, dtype=np.float32)

    for block_name, block_weight in block_weights.items():
        matrix = artifacts.block_matrices.get(block_name)
        if matrix is None:
            continue
        matrix_csr = cast(sparse.csr_matrix, matrix)
        seed_vec = matrix_csr[seed_idx]
        sim = matrix_csr.dot(seed_vec.T).toarray().ravel().astype(np.float32)
        base_score += np.float32(block_weight) * sim

    seed_weight = artifacts.weight_values[seed_idx]
    seed_weight_value = None if np.isnan(seed_weight) else float(seed_weight)
    penalty = _weight_penalty_vector(
        weight_values=artifacts.weight_values,
        seed_weight=seed_weight_value,
        strength=weight_penalty_strength,
        max_gap=weight_penalty_max_gap,
    )

    final_score = (base_score * penalty) + (np.float32(rating_weight) * artifacts.rating_bonus)
    final_score[seed_idx] = -np.inf

    ranked_idx = np.argsort(-final_score)
    top_idx = [idx for idx in ranked_idx if np.isfinite(final_score[idx])][:k]
    out = df.iloc[top_idx].copy()
    out["score"] = final_score[top_idx]
    out = out.sort_values("score", ascending=False)

    if print_results:
        seed_name = df.iloc[seed_idx].get("name", "")
        print(f"Recommendations for '{seed_name}' (id={game_id_str}):")
        rows = []
        for _, row in out.iterrows():
            rows.append(
                {
                    "name": row.get("name", ""),
                    "score": f"{row.get('score', 0):.3f}",
                    "avg_rating": row.get("rating_average", ""),
                    "weight": row.get("weight_average", ""),
                    "year": row.get("year_published", ""),
                    "url": f"https://boardgamegeek.com/boardgame/{row.get('id')}",
                }
            )

        disp = pd.DataFrame(rows)
        with pd.option_context("display.max_colwidth", 60):
            print(disp.to_string(index=False))

    return out
