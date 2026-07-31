from boardgame_db import BoardGameDB
from utils import clear_cache
from itertools import combinations
import time

# clear_cache()
def main():
    min_rating_count = 200
    min_prop_appearances = 500
    min_combo_count = 200
    top_bottom_count = 10

    db = BoardGameDB()
    df_games = db.df_games

    df_games = df_games[df_games["rating_count"] > min_rating_count].copy()
    print(f"Filtered to {len(df_games)} games with >{min_rating_count} ratings\n")

    # Build mapping: property -> set of game index labels
    prop_to_idx = {}
    for idx, props in df_games["properties"].items():
        if not props:
            continue
        for p in props:
            prop_to_idx.setdefault(p, set()).add(idx)

    # Optionally prune properties that appear fewer than min_prop_count times
    properties = [p for p, s in prop_to_idx.items() if len(s) >= min_prop_appearances]

    results = []
    start = time.time()
    for combo in combinations(properties, 2):
        a, b = combo
        ids = prop_to_idx.get(a, set()) & prop_to_idx.get(b, set())
        if ids:
            df_combo = df_games.loc[list(ids)]
            # skip if less than n games to avoid noise
            if len(df_combo) < min_combo_count:
                continue

            avg_rating = df_combo["rating"].mean()
            results.append((", ".join(combo), avg_rating, len(ids)))

    results.sort(key=lambda x: x[1], reverse=True)
    duration = time.time() - start

    print(f"Computed {len(results)} combos in {duration:.2f}s")
    print(f"Top {top_bottom_count} combinations:")
    for combo_str, avg_rating, count in results[:top_bottom_count]:
        print(f"{combo_str}: {avg_rating:.2f} (count: {count})")

    print(f"\nBottom {top_bottom_count} combinations:")
    for combo_str, avg_rating, count in results[-top_bottom_count:]:
        print(f"{combo_str}: {avg_rating:.2f} (count: {count})")


if __name__ == "__main__":
    main()
