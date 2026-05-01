from flask import Response, jsonify
import pandas as pd


def to_json_full(input: pd.Series) -> Response:
    return jsonify(input.to_dict())

def to_json_card(input: pd.Series) -> Response:
    return jsonify({
        "id": input["id"],
        "name": input["name"],
        "description": input["short_description"],
        "year": input["year_published"],
        "rating": input["average_rating"],
        "weight": input["weight_average"],
        "ranks": input["ranks"],
        "min_players": input["min_players"],
        "max_players": input["max_players"],
        "min_playtime": input["min_playtime"],
        "max_playtime": input["max_playtime"],
        "thumbnail": input["thumbnail"],

    })

def to_json_cards(input: pd.DataFrame) -> Response:
    return jsonify([to_json_card(row) for _, row in input.iterrows()])