"""Lightweight regression smoke test for BoardGameDB.

Run this after refactors to verify the core data-loading and lookup paths still work:

    python smoke_test.py
"""

from __future__ import annotations

import sys

from boardgame_db import BoardGameDB


def main() -> int:
    db = BoardGameDB()

    assert not db.df_games.empty, "BoardGameDB loaded no games"
    assert "id" in db.df_games.columns, "Missing required id column"

    sample_game = db.df_games.iloc[0]
    sample_id = str(sample_game["id"])
    sample_name = str(sample_game["name"])

    game_by_id = db.get_game_by_id(sample_id)
    assert game_by_id is not None, f"Could not fetch game by id {sample_id}"
    assert str(game_by_id["id"]) == sample_id, "Fetched game id mismatch"

    games_by_ids = db.get_games_by_ids([sample_id])
    assert games_by_ids is not None, "get_games_by_ids returned None"
    assert len(games_by_ids) == 1, "get_games_by_ids returned the wrong number of rows"
    assert str(games_by_ids.iloc[0]["id"]) == sample_id, "get_games_by_ids order/value mismatch"

    if db.search_engine is not None and sample_name:
        search_term = sample_name.split(" ")[0]
        matches = db.search_games(search_term, n=3, threshold=50)
        assert matches is not None, "search_games returned None"

    if "properties" in db.df_games.columns:
        assert db.df_games["properties"].notna().any(), "properties column was not populated"

    print("Smoke test passed: core load and lookup paths are working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())