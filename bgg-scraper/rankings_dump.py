
import os

import cloudscraper
from dotenv import load_dotenv
import pandas as pd
from web_automator import BrowserWrapper

from utils import get_today_date


def fetch_rankings_dump() -> pd.DataFrame:
    bgg_username = os.getenv("BGG_USERNAME", None)
    bgg_password = os.getenv("BGG_PASSWORD", None)

    if not bgg_username or not bgg_password:
        print("BGG_USERNAME and BGG_PASSWORD must be set in the .env file")
        exit(1)

    print("Fetching dump of rankings...")

    with BrowserWrapper().start_browser(headless=True, block_images=True) as browser:
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

        page.goto("https://boardgamegeek.com/data_dumps/bg_ranks")

        with page.page.expect_download() as download_info:
            page.click("div#maincontent a")

        download = download_info.value
        download.save_as(f"downloads/{download.suggested_filename}")

        # unzip the file and rename the .csv file inside
        import zipfile
        with zipfile.ZipFile(f"downloads/{download.suggested_filename}", 'r') as zip_ref:
            zip_ref.extractall("downloads")
            extracted_files = zip_ref.namelist()
            if len(extracted_files) == 1:
                new_file_name = f"data/ranks/ranks_{get_today_date()}.csv"
                os.rename(f"downloads/{extracted_files[0]}", new_file_name)
                os.remove(f"downloads/{download.suggested_filename}")

                return pd.read_csv(new_file_name)
            else:
                print("Unexpected number of files in the zip archive")
                exit(1)
        
        print("Download completed and dump extracted")


def filter_rankings(df_ranks: pd.DataFrame) -> pd.DataFrame:
    print("Filtering rankings...")
    # print(df_ranks.columns)

    df_ranks = df_ranks[['id','name', 'usersrated', 'yearpublished', 'is_expansion']]


    df_ranks = df_ranks[
        (df_ranks['usersrated'] >= 100) & 
        # (df_ranks['yearpublished'] >= 1990) & 
        # (df_ranks['yearpublished'] >= 2025) &
        (df_ranks['is_expansion'] == False)
    ]

    print(f"\nTOTAL GAMES AFTER FILTERING: {len(df_ranks)}\n")
    print(df_ranks.head())

    file_path = f"data/ranks/ranks_{get_today_date()}_filtered.csv"
    df_ranks.to_csv(file_path, index=False)
    print(f"\nSaved filtered ranks to {file_path}\n")

    return df_ranks

if __name__ == "__main__":
    load_dotenv()
    df_ranks = fetch_rankings_dump()
    df_filtered_ranks = filter_rankings(df_ranks)