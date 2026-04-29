import ast
import json

from dotenv import load_dotenv
import pandas as pd

from utils import get_today_date, normalize_whitespace_and_newlines

def parse_json_column(json_value):
    if pd.isna(json_value):
        return None
    if isinstance(json_value, dict):
        return json_value
    if isinstance(json_value, str):
        try:
            return json.loads(json_value)
        except json.JSONDecodeError:
            pass

        try:
            return ast.literal_eval(json_value)
        except (ValueError, SyntaxError):
            print(f"Error decoding JSON: {json_value[:100]}...")
            return None
    return None
    

def extract_details(json_data: dict) -> dict:
    credit_role_mapping = {
        "boardgamedesigner": "boardgame_designer",
        "boardgamesolodesigner": "boardgame_solo_designer",
        "boardgameartist": "boardgame_artist",
        "boardgamepublisher": "boardgame_publisher",
        "boardgamedeveloper": "boardgame_developer",
        "boardgamegraphicdesigner": "boardgame_graphic_designer",
        "boardgamesculptor": "boardgame_sculptor",
        "boardgameeditor": "boardgame_editor",
        "boardgamewriter": "boardgame_writer",
        "boardgameinsertdesigner": "boardgame_insert_designer",
    }
        
    credits = []
    for link in json_data.get("links", {}).keys():
        if link in credit_role_mapping:
            credit_entries = json_data.get("links", {}).get(link, [])
            if isinstance(credit_entries, list) and credit_entries:
                mapped_role = credit_role_mapping[link]
                credits.append({
                    "role": mapped_role,
                    "names": [credit.get("name") for credit in credit_entries]
                })

    expansions = []
    for expansion in json_data.get("links", {}).get("boardgameexpansion", []):
        expansions.append({
            "id": expansion.get("objectid"),
            "name": expansion.get("name"),
            "url": expansion.get("canonical_link"),
        })

    stats = json_data.get("stats", {})

    return {
        "id": json_data.get("id"),
        "name": json_data.get("name"),
        "alternate_names": [alt_name.get("name") for alt_name in json_data.get("alternatenames", [])],
        "year_published": json_data.get("yearpublished"),
        "short_description": json_data.get("short_description"),
        "description": json_data.get("description"),
        # "wiki": json_data.get("wiki"),
        "website_url": json_data.get("website", {}).get("url"),
        "thumbnail_url": json_data.get("images", {}).get("previewthumb"),
        "image_url": json_data.get("images", {}).get("original"),
        "player_counts": json_data.get("polls", {}).get("userplayers", {}),
        "min_players": json_data.get("minplayers"),
        "max_players": json_data.get("maxplayers"),
        "min_playtime": json_data.get("minplaytime"),
        "max_playtime": json_data.get("maxplaytime"),
        "min_age": json_data.get("minage"),
        "weight": json_data.get("polls", {}).get("boardgameweight"),
        "instructional_video_id": json_data.get("instructional_videoid"),
        "summary_video_id": json_data.get("summary_videoid"),
        "playthrough_video_id": json_data.get("playthrough_videoid"),
        "focus_video_id": json_data.get("focus_videoid"),
        "howtoplay_video_id": json_data.get("howtoplay_videoid"),
        # "has_danish_edition": any(
        #     "danish" in version.get("name", "").lower()
        #     for version in json_data.get("links", {}).get("boardgameversion", [])
        # ),
        "categories": [category.get("name") for category in json_data.get("links", {}).get("boardgamecategory", [])],
        "mechanics": [mechanic.get("name") for mechanic in json_data.get("links", {}).get("boardgamemechanic", [])],
        "honors": [honor.get("name") for honor in json_data.get("links", {}).get("boardgamehonor", [])],
        "credits": credits,
        "expansions": expansions,
        "reimplementation": [{
            "id": reimpl.get("objectid"),
            "name": reimpl.get("name"),
            "url": reimpl.get("canonical_link"),
        } for reimpl in json_data.get("links", {}).get("reimplementation", [])],
        "families": [family.get("name") for family in json_data.get("links", {}).get("boardgamefamily", [])],
        "subdomains": [subdomain.get("name") for subdomain in json_data.get("links", {}).get("boardgamesubdomain", [])],
        "url": json_data.get("canonical_link"),
        "ranks": [{"category": rank.get("shortprettyname"), "rank": rank.get("rank"), "bayes_average": rank.get("baverage")} for rank in json_data.get("rankinfo", [])],
        "language_dependence": json_data.get("polls", {}).get("languagedependence"),
        "rating_count": stats.get("usersrated"),
        "average_rating": stats.get("average"),
        "bayes_average_rating": stats.get("baverage"),
        "stddev_rating": stats.get("stddev"),
        # "average_weight": stats.get("avgweight"),
        # "weighting_count": stats.get("numweights"),
        "geeklist_count": stats.get("numgeeklists"),
        "trading_count": stats.get("numtrading"),
        "wanting_count": stats.get("numwanting"),
        "wish_count": stats.get("numwish"),
        "owned_count": stats.get("numowned"),
        "prev_owned_count": stats.get("numprevowned"),
        "comment_count": stats.get("numcomments"),
        "wishlist_comment_count": stats.get("numwishlistcomments"),
        "has_parts_count": stats.get("numhasparts"),
        "want_parts_count": stats.get("numwantparts"),
        "preorder_count": stats.get("numpreordered"),
        "want_to_play_count": stats.get("numwanttoplay"),
        "want_to_buy_count": stats.get("numwanttobuy"),
        "view_count": stats.get("views"),
        "play_count": stats.get("numplays"),
        "play_count_last_month": stats.get("numplays_month"),
        "fan_count": stats.get("numfans"),
    }

def extract_details_from_json_column(df_details: pd.DataFrame) -> pd.DataFrame:

    print("Extracting details from JSON column...")
    
    df_details["json"] = df_details["json"].apply(parse_json_column)

    extracted_data = []
    for index, row in df_details.iterrows():
        json_data = row["json"]
        if json_data is not None:
            extracted_data.append(extract_details(json_data))
        else:
            print(f"Missing JSON data for: https://boardgamegeek.com/boardgame/{row['id']}")
    
    df_extracted = pd.DataFrame(extracted_data)

    # run normalize_whitespace_and_newlines() on all object/string column
    for col in df_extracted.select_dtypes(include=["object", "string"]):
        df_extracted[col] = df_extracted[col].apply(normalize_whitespace_and_newlines)

    df_extracted.to_csv(f"data/final/final_{get_today_date()}.csv", index=False)

    print("Extraction complete. Extracted data saved to:", f"data/final/final_{get_today_date()}.csv")

    return df_extracted


if __name__ == "__main__":
    load_dotenv()
    
    df_details = pd.read_csv(f"data/details/details_{get_today_date()}.csv")
    df_final = extract_details_from_json_column(df_details)
    print(df_final.head())