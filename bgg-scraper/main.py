import json
import os

from dotenv import load_dotenv
import pandas as pd

from create_df_games import create_df_games
from create_final_dataset import create_final_dataset
from fetch_boardgame_details_api import fetch_bgg_api_data
from load_data import calc_boardgame_ids_to_scrape, update_scrape_metadata
from rankings_dump import filter_rankings, fetch_rankings_dump
from fetch_boardgame_details import pull_bgg_json_data
from utils import get_today_date

def main():
    load_dotenv()

    # filtered_rank_file = f"data/ranks/ranks_{get_today_date()}_filtered.csv"
    # if os.path.exists(filtered_rank_file):
    #     print(f"Filtered ranks file already exists at {filtered_rank_file}. Loading from file...")
    #     df_filtered_ranks = pd.read_csv(filtered_rank_file)
    # else:
    #     df_ranks = fetch_rankings_dump()
    #     df_filtered_ranks = filter_rankings(df_ranks)

    # ids_to_scrape = calc_boardgame_ids_to_scrape(df_filtered_ranks)

    # print(f"\nCalculated {len(ids_to_scrape)} board game IDs to scrape based on ranking and metadata criteria.\n")

    # data_dicts = fetch_bgg_api_data(boardgame_ids=ids_to_scrape)

    json_file = "downloads/results_20260506.json"
    data_dicts = json.load(open(json_file, "r", encoding="utf-8"))

    df_final = create_df_games(data_dicts)
    # df_final = create_final_dataset(data_dicts)

    print("\nUpdating scrape metadata...\n")
    update_scrape_metadata(df_final)

    print(df_final.head())

    final_file = f"data/final/final_{get_today_date()}.csv"

    print(f"\nSaving final data to CSV... ({final_file})")

    df_final.to_csv(final_file, index=False)

    # clean up intermediate files if they exist
    cleanup_paths = [
        f"data/ranks/ranks_{get_today_date()}.csv",
        f"downloads/results_{get_today_date()}.json",
        f"downloads/partial_results_{get_today_date()}.json",
    ]

    for path in cleanup_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

if __name__ == "__main__":
    main()