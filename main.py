from dotenv import load_dotenv

from extract_details_from_json_column import extract_details_from_json_column
from fetch_boardgame_details import fetch_boardgame_details
from rankings_dump import filter_rankings, fetch_rankings_dump
from utils import get_today_date

def main():
    load_dotenv()

    df_ranks = fetch_rankings_dump()
    df_filtered_ranks = filter_rankings(df_ranks)

    df_details = fetch_boardgame_details(boardgame_ids=df_filtered_ranks["id"].tolist())

    df_final = extract_details_from_json_column(df_details)

    print(df_final.head())




if __name__ == "__main__":
    main()