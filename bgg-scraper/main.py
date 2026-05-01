import json
import os

from dotenv import load_dotenv
import pandas as pd

from create_final_dataset import create_final_dataset
from load_data import calc_boardgame_ids_to_scrape
from rankings_dump import filter_rankings, fetch_rankings_dump
from fetch_boardgame_details import pull_bgg_json_data
from utils import get_today_date

def main():
    load_dotenv()


    df_ranks = fetch_rankings_dump()
    df_filtered_ranks = filter_rankings(df_ranks)

    ids_to_scrape = calc_boardgame_ids_to_scrape(df_filtered_ranks)

    data_dicts = pull_bgg_json_data(boardgame_ids=ids_to_scrape)

    df_final = create_final_dataset(data_dicts)

    print(df_final.head())

    print("\nSaving final data to CSV...")

    df_final.to_csv(f"data/final/final_{get_today_date()}.csv", index=False)

    # clean up intermediate files
    os.remove(f"data/ranks/ranks_{get_today_date()}.csv")
    os.remove(f"downloads/results_{get_today_date()}.json")
    os.remove(f"downloads/partial_results_{get_today_date()}.json")

if __name__ == "__main__":
    main()