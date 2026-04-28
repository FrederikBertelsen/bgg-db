from datetime import date
import json
import os
import re

from dotenv import load_dotenv
from pandas import DataFrame
import pandas as pd
from web_automator import BrowserWrapper, DataCollector, PageWrapper

from utils import get_today_date

def pull_json_from_page(page: PageWrapper) -> dict | None:
    """Attempt to pull the boardgame JSON from the page using multiple strategies."""
    try:
        json_str = page.evaluate_js("() => JSON.stringify(window.GEEK?.geekitemPreload?.item ?? null)")
        s = json_str.strip() if isinstance(json_str, str) else ""
        if s and s.lower() not in ("null", "undefined", ""):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    except Exception:
        pass

    return None

def reload_until_item_loaded(page: PageWrapper, browser: BrowserWrapper, url: str, wait_between_pages: int, max_attempts: int = 10, boardgame_id: str = "") -> tuple[dict | None, PageWrapper]:
    """Try multiple strategies to load the page JSON and return (parsed_dict_or_None, page).

    Strategies (in order): direct read, cache-busted navigation, hard reload,
    occasional fresh page creation. Returns (dict, page) on success or (None, page) on failure.
    """
    if boardgame_id == "":
        print("Warning: reload_until_item_loaded called without boardgame_id.")

    import time, random

    for attempt in range(1, max_attempts + 1):
        # 1) try direct read
        parsed = pull_json_from_page(page)
        if isinstance(parsed, dict):
            return parsed, page

        # 2) try cache-busted navigation
        try:
            ts = int(time.time() * 1000)
            cur = page.get_url() if hasattr(page, 'get_url') else url
            ts_url = f"{cur}&_={ts}" if "?" in cur else f"{cur}?_={ts}"
            page.goto(ts_url)
            page.sleep(wait_between_pages)
            page.wait_for_idle()
        except Exception:
            pass

        parsed = pull_json_from_page(page)
        if isinstance(parsed, dict):
            return parsed, page

        # 3) hard reload
        try:
            page.page.reload()
            page.sleep(wait_between_pages)
            page.wait_for_idle()
        except Exception:
            pass

        parsed = pull_json_from_page(page)
        if isinstance(parsed, dict):
            return parsed, page

        # 4) every few attempts, try a fresh page
        if attempt % 4 == 0 and browser is not None:
            try:
                new_page = browser.new_page()
                new_page.goto(url)
                new_page.sleep(wait_between_pages)
                new_page.wait_for_idle()
                parsed = pull_json_from_page(new_page)
                if isinstance(parsed, dict):
                    try:
                        page.close()
                    except Exception:
                        pass
                    return parsed, new_page
                try:
                    page.close()
                except Exception:
                    pass
                page = new_page
            except Exception:
                pass

        time.sleep(wait_between_pages + attempt * 0.2 + random.random() * 0.5)

    return None, page


def fetch_boardgame_details(boardgame_ids: list[str]) -> DataFrame:
    bgg_username = os.getenv("BGG_USERNAME", None)
    bgg_password = os.getenv("BGG_PASSWORD", None)
    wait_between_pages = int(os.getenv("WAIT_BETWEEN_PAGES", "2"))

    if not bgg_username or not bgg_password:
        print("BGG_USERNAME and BGG_PASSWORD must be set in the .env file")
        exit(1)

    print("Fetching boardgame details...")


    dc = DataCollector(print_on_flush=True, print_columns=["id"])
    
    dc.set_field("fetch_date", get_today_date())
    dc.set_current_row_as_base()

    total_failures = 0

    with BrowserWrapper().start_browser(headless=False, block_images=True) as browser:
        page = browser.new_page()

        for i, boardgame_id in enumerate(boardgame_ids):
            # print(f"\nFetching details for boardgame ID {boardgame_id}...")

            page.goto(f"https://boardgamegeek.com/boardgame/{boardgame_id}")
            page.sleep(wait_between_pages)
            page.wait_for_idle()

            # game_name = page.get_text("div.game-header-title-info h1 a")
            # game_year = page.get_text("div.game-header-title-info span.game-year")
            dc.set_fields({
                "id": boardgame_id,
                # "name": game_name.strip() if game_name else None,
                # "year": game_year.replace("(", "").replace(")", "").strip() if game_year else None,
            })

            # Attempt to load the game's JSON using the robust reload helper
            game_obj, page = reload_until_item_loaded(
                page,
                browser,
                f"https://boardgamegeek.com/boardgame/{boardgame_id}",
                wait_between_pages,
                max_attempts=10,
                boardgame_id=boardgame_id,
            )

            if isinstance(game_obj, dict):
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
                if "name" in game_obj and isinstance(game_obj["name"], str):
                    print(f"Name: {game_obj['name']}")
                # # save json to file
                # with open(f"{boardgame_id}.json", "w") as f:
                #     json.dump(game_obj, f, indent=4)
            else:
                print(f"Failed to fetch details for boardgame ID {boardgame_id}, skipping...")
                total_failures += 1

                if total_failures >= 10:
                    print(f"Total failures have reached {total_failures}, stopping the scraper to avoid further issues.")
                    exit(1)

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
