

import re
import cloudscraper
import pandas as pd

from utils import fetch_json

def fetch_short_description(scraper: cloudscraper.CloudScraper, boardgame_id: str | int) -> str | None:
    url = f"https://boardgamegeek.com/boardgame/{boardgame_id}"

    line_re = re.compile(r"\s*GEEK\.geekitemPreload = (.*}});\s*$", re.MULTILINE)
    
    json_data = fetch_json(scraper, url, line_re)
    if json_data:
        if "short_description" in json_data.get("item", {}):

            return json_data["item"]["short_description"]
        else:
            print(f"Fetched JSON does not contain 'short_description' key for boardgame ID {boardgame_id}.")
            return None
    
    print(f"Failed to fetch or parse geekitemPreload JSON for boardgame ID {boardgame_id}.")
    return None

if __name__ == "__main__":
    df_final = pd.read_csv("data/final/final_20260507.csv")
    print(f"Number of missing short_description values before fetching: {df_final['short_description'].isna().sum()}")
    exit()


    scraper = cloudscraper.create_scraper()
    boardgame_id = 167791

    short_description = fetch_short_description(scraper, boardgame_id)
    print(short_description)