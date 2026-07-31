from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from boardgame_db import BoardGameDB


GROUP_COLUMNS = ["mechanics", "components", "categories", "types", "themes"]
PROPERTY_COLUMN = "properties"
PROPERTY_FEATURE_LIMIT = 300
NUMERIC_COLUMNS = [
    "year_published",
    "min_age",
    "min_playing_time",
    "max_playing_time",
    "min_players",
    "max_players",
    "weight",
    "estimated_volume_cm3",
    "estimated_weight_kg",
]


def _ensure_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, tuple) or isinstance(value, set):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("{") or text.startswith("("):
            try:
                parsed = json.loads(text)
            except Exception:
                try:
                    parsed = ast.literal_eval(text)
                except Exception:
                    return [text]
            return _ensure_list(parsed)
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]
    return [str(value).strip()] if str(value).strip() else []


@dataclass
class SyntheticGame:
    label: str
    predicted_rating: float
    numeric_profile: dict[str, float]
    properties: list[str]
    group_counts: dict[str, int]
    feature_contributions: list[tuple[str, float]]


def _prepare_games(min_rating_count: int) -> pd.DataFrame:
    db = BoardGameDB()
    df_games = db.df_games.copy()

    before_count = len(df_games)
    df_games = df_games[pd.to_numeric(df_games["rating_count"], errors="coerce") > min_rating_count].copy()
    df_games["rating"] = pd.to_numeric(df_games["rating"], errors="coerce")
    df_games = df_games[df_games["rating"].notna()].copy()

    for column in NUMERIC_COLUMNS:
        if column in df_games.columns:
            df_games[column] = pd.to_numeric(df_games[column], errors="coerce")

    if PROPERTY_COLUMN not in df_games.columns:
        df_games[PROPERTY_COLUMN] = [[] for _ in range(len(df_games))]

    print(f"Filtered to {len(df_games)} games (from {before_count}) with >{min_rating_count} ratings")
    print(f"Average rating in filtered set: {df_games['rating'].mean():.2f}\n")
    return df_games


def build_feature_matrix(
    df_games: pd.DataFrame,
    min_token_count: int,
    feature_pool_size: int,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    feature_parts: list[pd.DataFrame] = []
    feature_pool: dict[str, list[str]] = {}

    property_lists = df_games[PROPERTY_COLUMN].apply(_ensure_list)
    property_sets = [set(items) for items in property_lists]
    property_counts = Counter(token for items in property_lists for token in items)
    property_candidates = [token for token, count in property_counts.most_common() if count >= min_token_count]
    property_candidates = property_candidates[: min(feature_pool_size, PROPERTY_FEATURE_LIMIT)]
    feature_pool[PROPERTY_COLUMN] = property_candidates

    for token in property_candidates:
        column_name = f"property::{token}"
        feature_parts.append(pd.DataFrame({column_name: [1 if token in token_set else 0 for token_set in property_sets]}, index=df_games.index))

    for group in GROUP_COLUMNS:
        grouped_lists = df_games[group].apply(_ensure_list)
        candidates = []
        feature_pool[group] = candidates

        feature_parts.append(pd.DataFrame({f"count::{group}": grouped_lists.apply(len)}, index=df_games.index))

    for column in NUMERIC_COLUMNS:
        if column not in df_games.columns:
            continue
        numeric = pd.to_numeric(df_games[column], errors="coerce")
        feature_parts.append(pd.DataFrame({column: numeric.fillna(numeric.median())}, index=df_games.index))

    X = pd.concat(feature_parts, axis=1).fillna(0)
    return X, feature_pool


def train_model(X: pd.DataFrame, y: pd.Series, alpha: float) -> tuple[StandardScaler, Ridge, np.ndarray]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=alpha)
    model.fit(X_scaled, y)

    predictions = model.predict(X_scaled)
    return scaler, model, predictions


def _feature_gains(X: pd.DataFrame, scaler: StandardScaler, model: Ridge) -> pd.Series:
    coefs = pd.Series(model.coef_, index=X.columns)
    scales = pd.Series(scaler.scale_, index=X.columns).replace(0, 1.0)
    return coefs / scales


def _select_numeric_profile(
    df_games: pd.DataFrame,
    feature_gains: pd.Series,
    direction: str,
) -> tuple[dict[str, float], dict[str, int]]:
    score_parts = []

    numeric_columns = [column for column in NUMERIC_COLUMNS if column in feature_gains.index and column in df_games.columns]
    if numeric_columns:
        numeric_frame = df_games[numeric_columns].apply(pd.to_numeric, errors="coerce")
        numeric_frame = numeric_frame.fillna(numeric_frame.median())
        score_parts.append(numeric_frame)

    count_frame = pd.DataFrame(
        {
            f"count::{group}": df_games[group].apply(lambda value: len(_ensure_list(value)))
            for group in GROUP_COLUMNS
            if f"count::{group}" in feature_gains.index
        },
        index=df_games.index,
    )
    if not count_frame.empty:
        score_parts.append(count_frame)

    score_frame = pd.concat(score_parts, axis=1)

    scores = score_frame.mul(feature_gains[score_frame.columns], axis=1).sum(axis=1)
    idx = scores.idxmax() if direction == "best" else scores.idxmin()
    numeric_profile = pd.to_numeric(df_games.loc[idx, NUMERIC_COLUMNS], errors="coerce").fillna(df_games[NUMERIC_COLUMNS].median()).to_dict()

    current_year = pd.Timestamp.now().year
    if "year_published" in numeric_profile and pd.notna(numeric_profile["year_published"]):
        numeric_profile["year_published"] = int(max(1800, min(current_year, round(float(numeric_profile["year_published"])))) )
    if "min_age" in numeric_profile and pd.notna(numeric_profile["min_age"]):
        numeric_profile["min_age"] = int(max(1, min(18, round(float(numeric_profile["min_age"])))) )

    count_targets = {
        group: int(round(score_frame.loc[idx, f"count::{group}"]))
        for group in GROUP_COLUMNS
        if f"count::{group}" in score_frame.columns
    }
    return numeric_profile, count_targets


def _select_properties(feature_pool: list[str], feature_gains: pd.Series, direction: str, top_n: int) -> list[str]:
    property_columns = [f"property::{token}" for token in feature_pool if f"property::{token}" in feature_gains.index]
    if not property_columns:
        return []

    gains = feature_gains[property_columns].sort_values(ascending=(direction == "worst"))
    selected = gains.head(top_n)
    return [column.split("::", 1)[1] for column in selected.index]


def _build_synthetic_row(
    feature_columns: list[str],
    numeric_profile: dict[str, float],
    property_tokens: list[str],
    group_counts: dict[str, int],
) -> pd.DataFrame:
    row = {column: 0 for column in feature_columns}

    for column, value in numeric_profile.items():
        row[column] = value

    for token in property_tokens:
        feature_name = f"property::{token}"
        if feature_name in row:
            row[feature_name] = 1

    for group, count in group_counts.items():
        row[f"count::{group}"] = count

    return pd.DataFrame([row], columns=feature_columns)


def _rank_contributions(
    feature_row: pd.DataFrame,
    scaler: StandardScaler,
    model: Ridge,
    top_n: int,
    direction: str,
) -> list[tuple[str, float]]:
    scaled = scaler.transform(feature_row)[0]
    contributions = pd.Series(scaled * model.coef_, index=feature_row.columns)
    contributions = contributions[contributions.abs() > 1e-9]

    if direction == "best":
        ranked = contributions.sort_values(ascending=False)
    else:
        ranked = contributions.sort_values(ascending=True)

    return list(ranked.head(top_n).items())


def _predict_synthetic_game(
    label: str,
    direction: str,
    df_games: pd.DataFrame,
    X: pd.DataFrame,
    scaler: StandardScaler,
    model: Ridge,
    feature_pool: dict[str, list[str]],
    top_n: int,
) -> SyntheticGame:
    feature_gains = _feature_gains(X, scaler, model)
    numeric_profile, count_targets = _select_numeric_profile(df_games, feature_gains, direction)
    property_tokens = _select_properties(feature_pool.get(PROPERTY_COLUMN, []), feature_gains, direction, top_n)

    feature_row = _build_synthetic_row(list(X.columns), numeric_profile, property_tokens, count_targets)
    predicted_rating = float(model.predict(scaler.transform(feature_row))[0])
    feature_contributions = _rank_contributions(feature_row, scaler, model, top_n, direction)

    return SyntheticGame(
        label=label,
        predicted_rating=predicted_rating,
        numeric_profile=numeric_profile,
        properties=property_tokens,
        group_counts=count_targets,
        feature_contributions=feature_contributions,
    )


def _closest_real_games(
    df_games: pd.DataFrame,
    X: pd.DataFrame,
    scaler: StandardScaler,
    synthetic: SyntheticGame,
    top_n: int,
) -> pd.DataFrame:
    feature_row = _build_synthetic_row(
        list(X.columns),
        synthetic.numeric_profile,
        synthetic.properties,
        synthetic.group_counts,
    )
    synthetic_scaled = scaler.transform(feature_row)[0]
    real_scaled = scaler.transform(X)
    distances = np.linalg.norm(real_scaled - synthetic_scaled, axis=1)

    ranked_positions = np.argsort(distances)[:top_n]
    closest = df_games.iloc[ranked_positions][["id", "name", "rating", "rating_count"]].copy()
    closest["distance"] = distances[ranked_positions]
    return closest.reset_index(drop=True)


def _print_synthetic_game(game: SyntheticGame, top_n: int) -> None:
    print(f"=== {game.label} ===")
    print(f"Predicted rating: {game.predicted_rating:.2f}\n")
    print("Numeric profile:")
    for column in NUMERIC_COLUMNS:
        value = game.numeric_profile.get(column)
        if value is not None:
            if float(value).is_integer():
                print(f"  {column}: {int(value)}")
            else:
                print(f"  {column}: {float(value):.2f}")
    print()

    print("Property bundle:")
    print(f"  properties: {', '.join(game.properties) if game.properties else '(none)'}")
    for group in GROUP_COLUMNS:
        print(f"  {group} count target: {game.group_counts.get(group, 0)}")
    print()

    print(f"Top {top_n} feature contributions:")
    for feature_name, contribution in game.feature_contributions:
        print(f"  {feature_name}: {contribution:+.3f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for plausible best and worst synthetic board games.")
    parser.add_argument("--min-rating-count", type=int, default=300)
    parser.add_argument("--min-token-count", type=int, default=50)
    parser.add_argument("--feature-pool-size", type=int, default=120)
    parser.add_argument("--model-alpha", type=float, default=2.0)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--nearest-n", type=int, default=5)
    args = parser.parse_args()

    df_games = _prepare_games(args.min_rating_count)
    X, feature_pool = build_feature_matrix(df_games, args.min_token_count, args.feature_pool_size)

    y = df_games["rating"].astype(float)
    scaler, model, predictions = train_model(X, y, args.model_alpha)

    train_rmse = float(np.sqrt(np.mean((y - predictions) ** 2)))
    train_mae = float(np.mean(np.abs(y - predictions)))

    best_game = _predict_synthetic_game(
        label="Best synthetic board game",
        direction="best",
        df_games=df_games,
        X=X,
        scaler=scaler,
        model=model,
        feature_pool=feature_pool,
        top_n=args.top_n,
    )
    worst_game = _predict_synthetic_game(
        label="Worst synthetic board game",
        direction="worst",
        df_games=df_games,
        X=X,
        scaler=scaler,
        model=model,
        feature_pool=feature_pool,
        top_n=args.top_n,
    )

    print("=== MODEL SUMMARY ===")
    print(f"Training RMSE: {train_rmse:.3f}")
    print(f"Training MAE:  {train_mae:.3f}\n")

    _print_synthetic_game(best_game, args.top_n)
    print(_closest_real_games(df_games, X, scaler, best_game, args.nearest_n).to_string(index=False))
    print()

    _print_synthetic_game(worst_game, args.top_n)
    print(_closest_real_games(df_games, X, scaler, worst_game, args.nearest_n).to_string(index=False))


if __name__ == "__main__":
    main()