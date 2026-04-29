from dotenv import load_dotenv
import pandas as pd

from old.extract_details_from_json_column import extract_details_from_json_column
from old.fetch_boardgame_details_old_2 import fetch_boardgame_details
from rankings_dump import filter_rankings, fetch_rankings_dump
from fetch_boardgame_details import pull_bgg_json_data
from utils import get_today_date

def main():
    load_dotenv()

    df_ranks = fetch_rankings_dump()
    df_filtered_ranks = filter_rankings(df_ranks)

    details_dicts = pull_bgg_json_data(boardgame_ids=df_filtered_ranks["id"].tolist())

    df_final = pd.DataFrame(details_dicts)

    # create types list for each category of ranks (except Overall Rank)
    #   ranks: [{'category': 'Overall Rank', 'rank': '489', 'bayes_average_rank': '7.01059'}, {'category': 'Party Rank', 'rank': '36', 'bayes_average_rank': '7.03261'}]
    df_final['types'] = df_final['ranks'].apply(lambda ranks: [r.get('category') for r in (ranks or []) if r.get('category') != 'Overall Rank'])

    print(df_final.head())

    print("\nSaving final data to CSV...")

    df_final.to_csv(f"data/final/final_{get_today_date()}.csv", index=False)

if __name__ == "__main__":
    main()