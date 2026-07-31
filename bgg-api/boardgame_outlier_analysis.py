from __future__ import annotations

import argparse
import ast
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from boardgame_db import BoardGameDB


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


def prepare_data(min_rating_count: int, min_playing_time_cutoff: int = 1) -> pd.DataFrame:
    """Load and filter game data."""
    db = BoardGameDB()
    df = db.df_games.copy()

    before = len(df)
    df = df[pd.to_numeric(df["rating_count"], errors="coerce") > min_rating_count].copy()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df[df["rating"].notna()].copy()
    df["min_playing_time"] = pd.to_numeric(df["min_playing_time"], errors="coerce")
    df["max_playing_time"] = pd.to_numeric(df["max_playing_time"], errors="coerce")
    df["min_players"] = pd.to_numeric(df["min_players"], errors="coerce")
    df["max_players"] = pd.to_numeric(df["max_players"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

    df = df[df["min_playing_time"] > min_playing_time_cutoff].copy()

    print(f"Loaded {len(df)} games (from {before}) with >{min_rating_count} ratings and >0 playing time\n")
    return df


def extract_property_features(df: pd.DataFrame, top_n: int) -> tuple[pd.DataFrame, list[str]]:
    """Extract property names and create one-hot features for top properties."""
    properties_expanded = []
    for idx, row in df.iterrows():
        props = _ensure_list(row.get("properties", []))
        properties_expanded.append(set(props))

    all_properties = set()
    for prop_set in properties_expanded:
        all_properties.update(prop_set)

    prop_counts = {}
    for prop in all_properties:
        prop_counts[prop] = sum(1 for pset in properties_expanded if prop in pset)

    top_props = sorted(prop_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_prop_names = [p[0] for p in top_props]

    feature_df = pd.DataFrame(index=df.index)
    for prop in top_prop_names:
        feature_df[f"prop_{prop}"] = [1 if prop in pset else 0 for pset in properties_expanded]

    print(f"Created one-hot features for top {len(top_prop_names)} properties")
    print(f"Most common properties: {', '.join(top_prop_names[:5])}\n")
    return feature_df, top_prop_names


def extract_count_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract count features: how many of each property type."""
    feature_df = pd.DataFrame(index=df.index)

    for col in ["mechanics", "components", "categories", "types", "themes"]:
        feature_df[f"count_{col}"] = df[col].apply(lambda x: len(_ensure_list(x)))

    return feature_df


def build_feature_matrix(
    df: pd.DataFrame,
    property_features: pd.DataFrame,
    count_features: pd.DataFrame,
    top_n_properties: int,
) -> tuple[pd.DataFrame, list[str]]:
    """Combine all features into a single matrix."""
    X = pd.DataFrame(index=df.index)

    X = pd.concat([X, property_features], axis=1)
    X = pd.concat([X, count_features], axis=1)

    numeric_cols = ["min_playing_time", "max_playing_time", "min_players", "max_players", "weight"]
    for col in numeric_cols:
        if col in df.columns:
            X[col] = df[col].fillna(df[col].median())

    X = X.fillna(0)

    feature_names = list(X.columns)
    print(f"Total features: {len(feature_names)}")
    print(f"  - {top_n_properties} individual properties")
    print(f"  - 5 count features (mechanics, components, categories, types, themes)")
    print(f"  - {len(numeric_cols)} numeric features\n")

    return X, feature_names


def train_and_predict(X: pd.DataFrame, y: pd.Series) -> tuple[LinearRegression, np.ndarray]:
    """Train linear regression and return model + predictions."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    y_pred = model.predict(X_scaled)
    return model, y_pred


def analyze_outliers(df: pd.DataFrame, y_pred: np.ndarray, top_n: int) -> None:
    """Find and display outlier games."""
    df_analysis = df[["id", "name", "rating", "rating_count", "min_playing_time", "max_playing_time", "weight"]].copy()
    df_analysis["predicted_rating"] = y_pred
    df_analysis["residual"] = df["rating"] - y_pred
    df_analysis["residual_pct"] = (df_analysis["residual"] / y_pred * 100).round(2)

    baseline = df["rating"].mean()
    df_analysis["baseline_diff"] = df["rating"] - baseline

    print("=== OVERPERFORMERS (Good when expected to be bad) ===\n")
    overperformers = df_analysis.nlargest(top_n, "residual")
    display_cols = ["name", "rating", "predicted_rating", "residual", "residual_pct", "rating_count"]
    print(overperformers[display_cols].to_string(index=False, formatters={
        "rating": "{:.2f}".format,
        "predicted_rating": "{:.2f}".format,
        "residual": "{:+.2f}".format,
        "residual_pct": "{:+.1f}%".format,
    }))
    print()

    print("=== UNDERPERFORMERS (Bad when expected to be good) ===\n")
    underperformers = df_analysis.nsmallest(top_n, "residual")
    print(underperformers[display_cols].to_string(index=False, formatters={
        "rating": "{:.2f}".format,
        "predicted_rating": "{:.2f}".format,
        "residual": "{:+.2f}".format,
        "residual_pct": "{:+.1f}%".format,
    }))
    print()

    print("=== MODEL PERFORMANCE ===")
    rmse = np.sqrt(np.mean((df["rating"] - y_pred) ** 2))
    mae = np.mean(np.abs(df["rating"] - y_pred))
    r_squared = 1 - np.sum((df["rating"] - y_pred) ** 2) / np.sum((df["rating"] - baseline) ** 2)
    print(f"RMSE: {rmse:.3f}")
    print(f"MAE:  {mae:.3f}")
    print(f"R²:   {r_squared:.3f}\n")

    return df_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Find board games that outperform or underperform expectations.")
    parser.add_argument("--min-rating-count", type=int, default=300)
    parser.add_argument("--top-n-properties", type=int, default=40)
    parser.add_argument("--top-n-outliers", type=int, default=15)
    args = parser.parse_args()

    df = prepare_data(args.min_rating_count)

    property_features, top_props = extract_property_features(df, args.top_n_properties)
    count_features = extract_count_features(df)
    X, feature_names = build_feature_matrix(df, property_features, count_features, args.top_n_properties)

    y = df["rating"].values

    model, y_pred = train_and_predict(X, y)

    df_analysis = analyze_outliers(df, y_pred, args.top_n_outliers)


if __name__ == "__main__":
    main()
