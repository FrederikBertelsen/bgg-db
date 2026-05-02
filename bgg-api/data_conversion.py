import ast

from flask import Response, jsonify
import pandas as pd
import numpy as np
from numbers import Integral, Real
import json


def to_json_full(input: pd.Series) -> Response:
    return jsonify(_normalize_dict(input.to_dict()))


def to_json_card(input: pd.Series) -> dict:
    card = {
        "id": input["id"],
        "name": input["name"],
        "short_description": input["short_description"],
        "year_published": input["year_published"],
        "rating_average": input["rating_average"],
        "weight_average": input["weight_average"],
        "ranks": input["ranks"],
        "min_players": input["min_players"],
        "max_players": input["max_players"],
        "min_playtime": input["min_playtime"],
        "max_playtime": input["max_playtime"],
        "thumbnail_url": input["thumbnail_url"],
        "score": input.get("score", None)
    }

    return _normalize_dict(card)


def to_json_cards(input: pd.DataFrame) -> Response:
    return jsonify([to_json_card(row) for _, row in input.iterrows()])


def _normalize_value(v):
    if v is None:
        return None
    # pandas NA values
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    # Use abstract numeric ABCs to safely detect numeric scalar types
    # Exclude bools from Integral check because bool is a subclass of int
    if isinstance(v, Integral) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, Real) and not isinstance(v, bool):
        # Real also matches integers, so keep Integral check first
        return float(v)
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (np.ndarray, list, tuple, set)):
        return [ _normalize_value(x) for x in list(v) ]
    if isinstance(v, dict):
        return _normalize_dict(v)
    # pandas Series
    if isinstance(v, pd.Series):
        return _normalize_dict(v.to_dict())
    # fallback for JSON plainness
    if isinstance(v, (str, int, float, bool)):
        return v
    try:
        return json.loads(json.dumps(v, default=str))
    except Exception:
        return str(v)


def _normalize_dict(d: dict) -> dict:
    return { k: _normalize_value(v) for k, v in d.items() }



def parse_json_like_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Detect columns that look like stringified lists/dicts and parse them.

    Uses ast.literal_eval on values that start with '[' or '{'. A column is
    converted only if at least half of sampled candidate values successfully
    parse to a list or dict to avoid accidental conversion of ordinary strings.
    """
    obj_cols = df.select_dtypes(include=["object"]).columns
    for col in obj_cols:
        sample = df[col].dropna().astype(str).head(50)
        if sample.empty:
            continue
        candidates = sample[sample.str.match(r"^\s*[\[\{]")]
        if candidates.empty:
            continue

        success = 0
        for v in candidates:
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, (list, dict)):
                    success += 1
            except Exception:
                pass

        if success / len(candidates) >= 0.5:
            def _conv(val):
                if pd.isna(val):
                    return val
                try:
                    parsed = ast.literal_eval(str(val))
                    return parsed
                except Exception:
                    return val
            df[col] = df[col].apply(_conv)

    return df