# app.py
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
import pandas as pd
import datetime

from boardgame_db import BoardGameDB
from data_conversion import *
from utils import clear_cache

app = Flask(__name__)
load_dotenv()

db = BoardGameDB()

@app.route("/games/<int:id>")
def game(id: int): # full_game_info
    print(f"[{datetime.datetime.now()}] games {id}")
    row = db.get_game_by_id(str(id))
    if row is None:
        return jsonify({"error": "Game not found", "id": id}), 404
    
    return jsonify(to_json_full(row))

@app.route("/cards/<ids_str>")
def cards(ids_str: str): # list[game_card]
    print(f"[{datetime.datetime.now()}] cards {ids_str}")
    ids = [i for i in ids_str.split(",") if i.isdigit()]
    if not ids:
        return jsonify({"error": "No valid game IDs provided"}), 400

    if len(ids) == 1:
        return jsonify({"error": "Provide at least two game IDs for this endpoint"}), 400

    rows = db.get_games_by_ids(ids)
    if rows is None or len(rows) == 0:
        return jsonify({"error": "No games found for provided IDs"}), 404

    return jsonify(to_json_cards(rows))

@app.route("/niches/<niche_name>")
def niche(niche_name: str): # niche_info
    print(f"[{datetime.datetime.now()}] niche {niche_name}")
    row = db.get_niche_by_name(niche_name)
    if row is None:
        return jsonify({"error": "Niche not found", "name": niche_name}), 404

    # only first 20 game_ids for the niche, to avoid too much data in the response
    game_ids = row.get("games_ids", [])[:20]
    game_rows = db.get_games_by_ids(game_ids) if game_ids else None
    row["games"] = [to_json_card(game_row) for _, game_row in game_rows.iterrows()] if game_rows is not None else []
    row.pop("games_ids")

    return jsonify(to_json_full(row))

@app.route("/niches/<niche_name>/games")
def niche_games(niche_name: str): # list[game_card]
    print(f"[{datetime.datetime.now()}] niche_games {niche_name}")
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

    return jsonify(to_json_cards(rows))

@app.route("/search/<search_term>")
def search(search_term: str): # list[game_card]
    print(f"[{datetime.datetime.now()}] search {search_term}")
    if not search_term:
        return jsonify({"error": "Empty search term"}), 400

    n = request.args.get("n", default=10, type=int)

    rows = db.search_games(search_term)
    if rows is None or len(rows) == 0:
        return jsonify([])

    if isinstance(rows, (list, tuple)):
        rows = rows[:n]

    return jsonify(to_json_cards(rows))


@app.route("/autocomplete/<search_term>")
def autocomplete_search(search_term: str): # list[str]
    print(f"[{datetime.datetime.now()}] autocomplete {search_term}")
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
    print(f"[{datetime.datetime.now()}] recommend {game_id}")
    n = request.args.get("n", default=10, type=int)
    min_score = request.args.get("min_score", default=0.5, type=float)
    min_rating = request.args.get("min_rating", default=6.5, type=float)

    try:
        recs = db.recommend_games(game_id, n=n, min_score=min_score, min_rating=min_rating)
    except ValueError:
        return jsonify({"error": "Game not found", "id": game_id}), 404

    if recs is None or len(recs) == 0:
        return jsonify([])

    return jsonify(to_json_cards(recs))

@app.route("/injection/<game_id>")
def bgg_injection(game_id: str): # dict

    min_score = request.args.get("min_score", default=0.5, type=float)
    min_rating = request.args.get("min_rating", default=6.5, type=float)
        
    print(f"[{datetime.datetime.now()}] injection {game_id}")
    row = db.get_game_by_id(game_id)
    if row is None:
        return jsonify({"error": "Game not found", "id": game_id}), 404
    
    recommendations = db.recommend_games(game_id, n=20, min_score=min_score, min_rating=min_rating)
    row["recommendations"] = to_json_cards(recommendations) if recommendations is not None else []
    
    return jsonify(bgg_injection_data(row))


@app.route("/update-db", methods=["GET", "POST"])
def update_db():
    payload = request.get_json(silent=True) or {}
    key = request.args.get("key", default=payload.get("key", ""), type=str)
    if key != os.getenv("UPDATE_DB_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    global db

    print(f"[{datetime.datetime.now()}] update-db")
    try:
        clear_cache()
        db = BoardGameDB()
        return jsonify({"message": "Database updated successfully"})
    except Exception as e:
        return jsonify({"error": "Failed to update database", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443, debug=True)