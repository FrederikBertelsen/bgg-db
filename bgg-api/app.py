# app.py
from flask import Flask, jsonify, request
import pandas as pd

from boardgame_db import BoardGameDB
from data_conversion import *

app = Flask(__name__)
db = BoardGameDB()

not_found_error = jsonify({"error": "not found"}), 404
no_input_error = jsonify({"error": "no input provided"}), 400


@app.route("/games/<int:id>")
def game(id: int): # full_game_info
    row = db.get_game_by_id(str(id))
    if row is None:
        return not_found_error
    
    return to_json_full(row)

@app.route("/cards/<ids_str>")
def cards(ids_str: str): # list[game_card]
    ids = [i for i in ids_str.split(",") if i.isdigit()]
    if not ids or len(ids) == 1:
        return no_input_error

    rows = db.get_games_by_ids(ids)
    if rows is None:
        return not_found_error

    return to_json_cards(rows)

@app.route("/search/<search_term>")
def search(search_term: str): # list[game_card]
    if not search_term:
        return no_input_error

    n = request.args.get("n", default=10, type=int)

    rows = db.search_games(search_term)
    if rows is None or len(rows) == 0:
        return not_found_error

    if isinstance(rows, (list, tuple)):
        rows = rows[:n]

    return to_json_cards(rows)


@app.route("/autocomplete/<search_term>")
def autocomplete_search(search_term: str): # list[str]
    if not search_term:
        return no_input_error
    
    n = request.args.get("n", default=5, type=int)

    results = db.autocomplete_search(search_term, n=n)
    if results is None or len(results) == 0:
        return jsonify([])

    names = [match for match, score in results]

    return jsonify(names)

@app.route("/recommend/<game_id>")
def recommend_games(game_id: str): # list[game_card]
    n = request.args.get("n", default=5, type=int)

    try:
        recs = db.recommend_games(game_id, n=n)
    except ValueError:
        return not_found_error

    if recs is None or len(recs) == 0:
        return not_found_error

    return to_json_cards(recs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)