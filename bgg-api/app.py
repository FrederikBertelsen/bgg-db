# app.py
from flask import Flask, jsonify, request
import pandas as pd

from boardgame_db import BoardGameDB
from data_conversion import *

app = Flask(__name__)
db = BoardGameDB()

@app.route("/games/<int:id>")
def game(id: int): # full_game_info
    row = db.get_game_by_id(str(id))
    if row is None:
        return jsonify({"error": "Game not found", "id": id}), 404
    
    return to_json_full(row)

@app.route("/cards/<ids_str>")
def cards(ids_str: str): # list[game_card]
    ids = [i for i in ids_str.split(",") if i.isdigit()]
    if not ids:
        return jsonify({"error": "No valid game IDs provided"}), 400

    if len(ids) == 1:
        return jsonify({"error": "Provide at least two game IDs for this endpoint"}), 400

    rows = db.get_games_by_ids(ids)
    if rows is None or len(rows) == 0:
        return jsonify({"error": "No games found for provided IDs"}), 404

    return to_json_cards(rows)

@app.route("/niches/<niche_name>")
def niche(niche_name: str): # niche_info
    row = db.get_niche_by_name(niche_name)
    if row is None:
        return jsonify({"error": "Niche not found", "name": niche_name}), 404

    # only first 20 game_ids for the niche, to avoid too much data in the response
    game_ids = row.get("games_ids", [])[:20]
    game_rows = db.get_games_by_ids(game_ids) if game_ids else None
    row["games"] = [to_json_card(game_row) for _, game_row in game_rows.iterrows()] if game_rows is not None else []
    row.pop("games_ids")

    return to_json_full(row)

@app.route("/niches/<niche_name>/games")
def niche_games(niche_name: str): # list[game_card]
    row = db.get_niche_by_name(niche_name)
    if row is None:
        return jsonify({"error": "Niche not found", "name": niche_name}), 404

    game_ids = row.get("games_ids", [])
    if not game_ids:
        return jsonify([])
    
    start = request.args.get("start", default=0, type=int)
    end = request.args.get("end", default=start + 20, type=int)
    game_ids = game_ids[start:end]

    rows = db.get_games_by_ids(game_ids)
    if rows is None or len(rows) == 0:
        return jsonify({"error": "No games found for provided IDs"}), 404

    return to_json_cards(rows)

@app.route("/search/<search_term>")
def search(search_term: str): # list[game_card]
    if not search_term:
        return jsonify({"error": "Empty search term"}), 400

    n = request.args.get("n", default=10, type=int)

    rows = db.search_games(search_term)
    if rows is None or len(rows) == 0:
        return jsonify([])

    if isinstance(rows, (list, tuple)):
        rows = rows[:n]

    return to_json_cards(rows)


@app.route("/autocomplete/<search_term>")
def autocomplete_search(search_term: str): # list[str]
    if not search_term:
        return jsonify({"error": "Empty query"}), 400
    
    n = request.args.get("n", default=5, type=int)

    results = db.autocomplete_search(search_term, n=n)
    if results is None or len(results) == 0:
        return jsonify([])

    names = [match for match, score in results]

    return jsonify(names)

@app.route("/recommend/<game_id>")
def recommend_games(game_id: str): # list[game_card]
    n = request.args.get("n", default=10, type=int)

    try:
        recs = db.recommend_games(game_id, n=n)
    except ValueError:
        return jsonify({"error": "Game not found", "id": game_id}), 404

    if recs is None or len(recs) == 0:
        return jsonify([])

    return to_json_cards(recs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443, debug=True)