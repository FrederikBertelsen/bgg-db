from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from itertools import combinations

import pandas as pd

from boardgame_db import BoardGameDB


PROPERTY_COLUMNS = ["mechanics", "components", "categories", "types", "themes"]


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


def _prepare_games(min_rating_count: int) -> pd.DataFrame:
    db = BoardGameDB()
    df_games = db.df_games.copy()

    before_count = len(df_games)
    df_games = df_games[pd.to_numeric(df_games["rating_count"], errors="coerce") > min_rating_count].copy()
    df_games["rating"] = pd.to_numeric(df_games["rating"], errors="coerce")
    df_games = df_games[df_games["rating"].notna()].copy()

    print(f"Filtered to {len(df_games)} games (from {before_count}) with >{min_rating_count} ratings")
    print(f"Average rating in filtered set: {df_games['rating'].mean():.2f}\n")
    return df_games


def _explode_property(df_games: pd.DataFrame, column: str) -> pd.DataFrame:
    exploded = df_games[["rating", "rating_count", column]].copy()
    exploded[column] = exploded[column].apply(_ensure_list)
    exploded = exploded.explode(column)
    exploded[column] = exploded[column].astype(str).str.strip()
    exploded = exploded[exploded[column].notna() & (exploded[column] != "")]
    return exploded


def build_property_stats(df_games: pd.DataFrame, column: str, min_count: int, shrink: float) -> pd.DataFrame:
    exploded = _explode_property(df_games, column)
    baseline = float(df_games["rating"].mean())

    stats = (
        exploded.groupby(column, dropna=True)
        .agg(
            games=("rating", "size"),
            avg_rating=("rating", "mean"),
            rating_std=("rating", "std"),
        )
        .reset_index()
    )

    stats = stats[stats["games"] >= min_count].copy()
    if stats.empty:
        return stats

    stats["coverage_pct"] = (stats["games"] / len(df_games) * 100).round(2)
    stats["avg_rating"] = stats["avg_rating"].astype(float)
    stats["adjusted_rating"] = (
        (stats["games"] * stats["avg_rating"] + shrink * baseline) / (stats["games"] + shrink)
    )
    stats["delta_vs_baseline"] = stats["adjusted_rating"] - baseline
    stats["rating_std"] = stats["rating_std"].fillna(0.0)
    stats["property_type"] = column
    return stats.sort_values(["delta_vs_baseline", "games"], ascending=[False, False]).reset_index(drop=True)


def print_property_leaderboard(all_stats: pd.DataFrame, top_n: int) -> None:
    print("=== Property influence overall ===")
    if all_stats.empty:
        print("No property tokens met the minimum support threshold.\n")
        return

    all_stats = all_stats.copy()
    all_stats["property_name"] = all_stats[PROPERTY_COLUMNS].bfill(axis=1).iloc[:, 0]
    leaderboard = all_stats[["property_type", "property_name", "games", "coverage_pct", "avg_rating", "adjusted_rating", "delta_vs_baseline"]]

    fmt = {
        "coverage_pct": "{:.2f}".format,
        "avg_rating": "{:.2f}".format,
        "adjusted_rating": "{:.2f}".format,
        "delta_vs_baseline": "{:+.2f}".format,
    }

    print("Top properties by adjusted rating delta:")
    print(leaderboard.head(top_n).to_string(index=False, formatters=fmt))
    print()
    print("Bottom properties by adjusted rating delta:")
    print(leaderboard.tail(top_n).sort_values("delta_vs_baseline", ascending=True).to_string(index=False, formatters=fmt))
    print()


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def build_mechanic_pair_stats(
    df_games: pd.DataFrame,
    min_mechanic_count: int,
    min_pair_count: int,
    shrink: float,
) -> pd.DataFrame:
    mechanic_stats = build_property_stats(df_games, "mechanics", min_mechanic_count, shrink)
    if mechanic_stats.empty:
        return mechanic_stats

    frequent_mechanics = set(mechanic_stats["mechanics"])
    baseline = float(df_games["rating"].mean())

    pair_counts: Counter[tuple[str, str]] = Counter()
    pair_rating_sum: Counter[tuple[str, str]] = Counter()

    mechanics_series = df_games["mechanics"].apply(_ensure_list)
    ratings = df_games["rating"]

    for mech_list, rating in zip(mechanics_series, ratings, strict=False):
        filtered = sorted({m for m in mech_list if m in frequent_mechanics})
        if len(filtered) < 2:
            continue
        for a, b in combinations(filtered, 2):
            key = _pair_key(a, b)
            pair_counts[key] += 1
            pair_rating_sum[key] += float(rating)

    rows = []
    mechanic_means = mechanic_stats.set_index("mechanics")["adjusted_rating"].to_dict()

    for (a, b), count in pair_counts.items():
        if count < min_pair_count:
            continue
        mean_rating = pair_rating_sum[(a, b)] / count
        adjusted_rating = (count * mean_rating + shrink * baseline) / (count + shrink)
        expected_rating = (mechanic_means.get(a, baseline) + mechanic_means.get(b, baseline)) / 2
        rows.append(
            {
                "mechanic_a": a,
                "mechanic_b": b,
                "games": count,
                "avg_rating": mean_rating,
                "adjusted_rating": adjusted_rating,
                "synergy_vs_individuals": adjusted_rating - expected_rating,
            }
        )

    pair_stats = pd.DataFrame(rows)
    if pair_stats.empty:
        return pair_stats

    pair_stats["coverage_pct"] = (pair_stats["games"] / len(df_games) * 100).round(2)
    return pair_stats.sort_values(["synergy_vs_individuals", "games"], ascending=[False, False]).reset_index(drop=True)


def print_mechanic_pair_report(pair_stats: pd.DataFrame, top_n: int) -> None:
    print("=== Mechanic pair synergy ===")
    if pair_stats.empty:
        print("No mechanic pairs met the minimum support threshold.\n")
        return

    display = pair_stats[["mechanic_a", "mechanic_b", "games", "coverage_pct", "avg_rating", "adjusted_rating", "synergy_vs_individuals"]]
    fmt = {
        "coverage_pct": "{:.2f}".format,
        "avg_rating": "{:.2f}".format,
        "adjusted_rating": "{:.2f}".format,
        "synergy_vs_individuals": "{:+.2f}".format,
    }

    print("Best mechanic pairs (higher than their individual mechanic baselines):")
    print(display.head(top_n).to_string(index=False, formatters=fmt))
    print()
    print("Worst mechanic pairs (lower than their individual mechanic baselines):")
    print(display.tail(top_n).sort_values("synergy_vs_individuals", ascending=True).to_string(index=False, formatters=fmt))
    print()


def print_complexity_report(df_games: pd.DataFrame) -> None:
    print("=== Structural complexity ===")
    complexity = pd.DataFrame(
        {
            "mechanic_count": df_games["mechanics"].apply(lambda value: len(_ensure_list(value))),
            "component_count": df_games["components"].apply(lambda value: len(_ensure_list(value))),
            "category_count": df_games["categories"].apply(lambda value: len(_ensure_list(value))),
            "type_count": df_games["types"].apply(lambda value: len(_ensure_list(value))),
            "theme_count": df_games["themes"].apply(lambda value: len(_ensure_list(value))),
            "rating": df_games["rating"],
        }
    )

    for column in ["mechanic_count", "component_count", "category_count", "type_count", "theme_count"]:
        grouped = (
            complexity.groupby(column)
            .agg(games=("rating", "size"), avg_rating=("rating", "mean"))
            .reset_index()
            .sort_values(column)
        )
        if grouped.empty:
            continue
        print(f"Rating by {column.replace('_count', ' count')}:\n{grouped.to_string(index=False, formatters={'avg_rating': '{:.2f}'.format})}\n")

    corr = complexity[["mechanic_count", "component_count", "category_count", "type_count", "theme_count", "rating"]].corr(method="spearman")
    print("Spearman correlation with rating:")
    print(corr["rating"].drop("rating").sort_values(ascending=False).to_string(float_format="{:.3f}".format))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze how board game properties relate to rating.")
    parser.add_argument("--min-rating-count", type=int, default=300)
    parser.add_argument("--min-property-count", type=int, default=50)
    parser.add_argument("--min-mechanic-count", type=int, default=60)
    parser.add_argument("--min-pair-count", type=int, default=25)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--shrink", type=float, default=20.0)
    args = parser.parse_args()

    df_games = _prepare_games(args.min_rating_count)

    all_stats = []
    for column in PROPERTY_COLUMNS:
        stats = build_property_stats(df_games, column, args.min_property_count, args.shrink)
        if stats.empty:
            print(f"=== {column.title()} ===")
            print(f"No {column} tokens met the minimum support threshold of {args.min_property_count}.\n")
            continue
        all_stats.append(stats)
        print(f"=== {column.title()} ===")
        display = stats[[column, "games", "coverage_pct", "avg_rating", "adjusted_rating", "delta_vs_baseline"]]
        fmt = {
            "coverage_pct": "{:.2f}".format,
            "avg_rating": "{:.2f}".format,
            "adjusted_rating": "{:.2f}".format,
            "delta_vs_baseline": "{:+.2f}".format,
        }
        print("Best tokens:")
        print(display.head(args.top_n).to_string(index=False, formatters=fmt))
        print()
        print("Worst tokens:")
        print(display.tail(args.top_n).sort_values("delta_vs_baseline", ascending=True).to_string(index=False, formatters=fmt))
        print()

    if all_stats:
        combined = pd.concat(all_stats, ignore_index=True)
        combined = combined.sort_values(["delta_vs_baseline", "games"], ascending=[False, False]).reset_index(drop=True)
        print_property_leaderboard(combined, args.top_n)

    pair_stats = build_mechanic_pair_stats(df_games, args.min_mechanic_count, args.min_pair_count, args.shrink)
    print_mechanic_pair_report(pair_stats, args.top_n)

    print_complexity_report(df_games)


if __name__ == "__main__":
    main()