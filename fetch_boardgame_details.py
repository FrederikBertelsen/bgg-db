from datetime import date
import json
import os
import re

from dotenv import load_dotenv
from pandas import DataFrame
import pandas as pd
from web_automator import BrowserWrapper, DataCollector

from utils import get_today_date


def fetch_boardgame_details(boardgame_ids: list[str]) -> DataFrame:
    bgg_username = os.getenv("BGG_USERNAME", None)
    bgg_password = os.getenv("BGG_PASSWORD", None)
    wait_between_pages = int(os.getenv("WAIT_BETWEEN_PAGES", "1"))

    if not bgg_username or not bgg_password:
        print("BGG_USERNAME and BGG_PASSWORD must be set in the .env file")
        exit(1)

    print("Fetching boardgame details...")


    dc = DataCollector(print_on_flush=True, print_columns=["id", "name", "year"])
    
    dc.set_field("fetch_date", get_today_date())
    dc.set_current_row_as_base()

    with BrowserWrapper().start_browser(headless=False, block_images=True) as browser:
        page = browser.new_page()

        for i, boardgame_id in enumerate(boardgame_ids):
            # print(f"\nFetching details for boardgame ID {boardgame_id}...")

            page.goto(f"https://boardgamegeek.com/boardgame/{boardgame_id}")
            page.sleep(wait_between_pages)
            page.wait_for_idle()

            game_name = page.get_text("div.game-header-title-info h1 a")
            game_year = page.get_text("div.game-header-title-info span.game-year")
            dc.set_fields({
                "id": boardgame_id,
                "name": game_name.strip() if game_name else None,
                "year": game_year.replace("(", "").replace(")", "").strip() if game_year else None,
            })

            fail_count = 0
            json_str = None
            while not json_str:
                json_str = page.evaluate_js("() => JSON.stringify(window.GEEK?.geekitemPreload?.item ?? null)")
                if not json_str:
                    if fail_count >= 5:
                        print(f"Failed to fetch details for boardgame ID {boardgame_id} after {fail_count} attempts, skipping...")
                        break

                    fail_count += 1
                    print(f"Failed to fetch details for boardgame ID {boardgame_id}, retrying... (fail count: {fail_count})")

                    if fail_count == 3:
                        print("Refreshing the page...")
                        page.page.reload()

                    page.sleep(wait_between_pages)
                    page.wait_for_idle()

            if json_str:
                game_obj = json.loads(json_str)

                useful_fields = [
                    "id",
                    "name",
                    "yearpublished",
                    "short_description",
                    "primaryname",
                    "alternatenames",

                    "description",
                    "wiki",
                    "website",
                    "images",

                    "minplayers",
                    "maxplayers",
                    "minplaytime",
                    "maxplaytime",
                    "minage",
                    "instructional_videoid",
                    "summary_videoid",
                    "playthrough_videoid",
                    "focus_videoid",
                    "howtoplay_videoid",
                    "links",

                    "canonical_link",
                    "rankinfo",
                    "polls",
                    "stats",
                ]

                game_obj = {key: game_obj.get(key, None) for key in useful_fields}

                # # save json to file
                # with open(f"{boardgame_id}.json", "w") as f:
                #     json.dump(game_obj, f, indent=4)
            else:
                game_obj = None

            dc.set_fields({
                "json": game_obj,
            })

            dc.commit_row()

            if i % 100 == 0:
                print(f"\nFetched details for {i} boardgames so far, saving to file...\n")
                dc.to_dataframe().to_csv(f"data/details/details_{get_today_date()}.csv", index=False)



    df_details = dc.to_dataframe()
    df_details.to_csv(f"data/details/details_{get_today_date()}.csv", index=False)
    
    print(f"\nSaved details for {len(df_details)} boardgames to data/details/details_{get_today_date()}.csv\n")

    return df_details



if __name__ == "__main__":
    load_dotenv()
    df_test = fetch_boardgame_details(["167791"])
