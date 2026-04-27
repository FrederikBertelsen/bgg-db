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

    boardgame_base_url = "https://boardgamegeek.com/boardgame/"

    print("Fetching boardgame details... (OLD VERSION)")

    dc = DataCollector(print_on_flush=True, print_columns=["id", "name", "year"])
    with BrowserWrapper().start_browser(headless=False, block_images=True) as browser:
        page = browser.new_page()

        page.goto("https://boardgamegeek.com/login")
        page.wait_for_idle()

        if page.click("button[aria-label=\"I'm OK with that\"]"):
            print("Cookie banner accepted")
            page.wait_for_idle()

        page.login(
                login_url="https://boardgamegeek.com/login",

                username_selector="input#inputUsername",
                password_selector="input#inputPassword",
                submit_selector="button.btn.btn-lg.btn-primary",

                username=bgg_username,
                password=bgg_password,

                cookies_file="cookies/cookies.json",

                post_login_url="https://boardgamegeek.com",
                success_selector="gg-avatar-letter",
        )

        for game_id in boardgame_ids:
            url = f"{boardgame_base_url}{game_id}"

            page.goto(url + "/stats")
            page.sleep(wait_between_pages)

            game_name = page.get_text("div.game-header-title-info h1 a")
            game_year = page.get_text("div.game-header-title-info span.game-year")
            game_playing_time = page.get_text("p.gameplay-item-primary span[ng-if*='minplaytime']")

            dc.set_fields({
                "id": game_id,
                "name": game_name.strip() if game_name is not None else None,
                "year": game_year.strip() if game_year is not None else None,
                "playing_time": game_playing_time.strip() if game_playing_time is not None else None,
            })

            player_count_raw = page.get_text('li[itemprop="numberOfPlayers"]')
            dc.set_field("player_count_raw", player_count_raw.strip() if player_count_raw is not None else None)
            try:
                player_counts = re.findall(r"(\d+(?:\.\d+)?)", player_count_raw or "")
                if len(player_counts) > 0:
                    dc.set_field("standard_player_count", player_counts[0].strip())
                if len(player_counts) > 1:
                    dc.set_field("community_player_count", player_counts[1].strip())
                if len(player_counts) > 2:
                    dc.set_field("best_player_count", player_counts[2].strip())
            except:
                print(f"SOMETHINGS WRONG WITH PLAYER COUNT:\n{player_count_raw}")
                pass

            # fetch extra player count data
            # url: https://boardgamegeek.com/geekitempoll.php?action=view&itempolltype=numplayers&objectid=[BOARDGAME_ID]&objecttype=thing
            # data_url: https://boardgamegeek.com/geekpoll.php?action=results&pollid=[POLL_ID]
            poll_data_url = f"https://boardgamegeek.com/geekitempoll.php?action=view&itempolltype=numplayers&objectid={game_id}&objecttype=thing"
            



        
            stat_elms = page.locator("div.panel-body > ul > li.outline-item")
            for stat_elm in stat_elms.element_handles():
                stat_name = stat_elm.query_selector("div.outline-item-title")
                stat_value = stat_elm.query_selector("div.outline-item-description")
                if stat_name and stat_value:
                    dc.set_field(stat_name.inner_text().strip(), stat_value.inner_text().strip())
            
            page.goto(url)
            page.sleep(wait_between_pages)

            dc.set_field("image_url", page.get_attribute("div.game-primary a[href^='/image/'] img[src]", "src"))

            classification_elms = page.locator("div.game-description-classification li.feature")
            for class_elm in classification_elms.element_handles():
                try:
                    class_name = class_elm.query_selector("h4.feature-title")
                    if class_name:
                        class_name = class_name.inner_text()
                    if class_name in ['Type', 'Category', 'Mechanism', 'Integrates With']:
                        values = class_elm.query_selector_all("div.feature-description a")
                        values = [value.inner_text() for value in values]

                        dc.set_field(class_name, ", ".join(values))
                except:
                    pass

            page.goto(url + "/versions?showcount=50")
            page.sleep(wait_between_pages)

            sizes = page.locator("span[ng-if=\"ldata.displaytype==='dimensions'\"]").all_inner_texts()
            dc.set_field("sizes", list(set(sizes))[:5])


            page.goto(url + "/marketplace/stores")
            page.sleep(wait_between_pages)

            prices = page.locator("ul.shopping-listings > li.item-listing a[href] span.item-listing__btn-text").all_inner_texts()
            dc.set_field("prices", list(set(prices)))

            dc.commit_row()

    df_details = dc.to_dataframe()
    df_details.to_csv(f"data/details/details_old_{get_today_date()}.csv", index=False)

    return df_details



if __name__ == "__main__":
    load_dotenv()

    df_ranks = pd.read_csv(f"data/ranks/ranks_{get_today_date()}_filtered.csv")

    df_test = fetch_boardgame_details(boardgame_ids=df_ranks["id"].tolist())

    # print each key value pair in the dataframe
    for index, row in df_test.iterrows():
        print(f"Row {index}:")
        for key, value in row.items():
            print(f"  {key}: {value}")
