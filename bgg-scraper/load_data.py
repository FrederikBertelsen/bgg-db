

import json
import os

import pandas as pd

from utils import get_today_date

def load_scrape_metadata() -> pd.DataFrame:
    metadata_file = f"data/scrape_metadata.csv"
    if os.path.exists(metadata_file):
        return pd.read_csv(metadata_file)
    else:
        print(f"No scrape metadata file found at {metadata_file}. Returning empty DataFrame.")
        return pd.DataFrame()

def save_scrape_metadata(df_metadata: pd.DataFrame) -> None:
    metadata_file = f"data/scrape_metadata.csv"
    if os.path.exists(metadata_file):
        df_metadata.to_csv(metadata_file, mode='a', header=False, index=False)
    else:
        df_metadata.to_csv(metadata_file, index=False)

def update_scrape_metadata(df_final: pd.DataFrame):
    df_metadata = load_scrape_metadata()

    new_rows = []
    for _, row in df_final.iterrows():
        game_id = row["id"]
        existing_metadata = df_metadata[df_metadata["id"] == game_id]

        # update or add metadata for this game_id
        if not existing_metadata.empty:
            df_metadata.loc[df_metadata["id"] == game_id, ["usersrated", "last_scraped_date"]] = [row["usersrated"], get_today_date()]
        else:

            new_metadata = {
                "id": game_id,
                "usersrated": row["usersrated"],
                "last_scraped_date": get_today_date()
            }
            new_rows.append(new_metadata)
        
    df_metadata = pd.concat([df_metadata, pd.DataFrame(new_rows)], ignore_index=True)
    
    save_scrape_metadata(df_metadata)

def calc_boardgame_ids_to_scrape(df_filtered_ranks: pd.DataFrame) -> list[str]:
    df_metadata = load_scrape_metadata()

    ids_to_scrape = []
    for _, row in df_filtered_ranks.iterrows():
        game_id = row["id"]

        existing_metadata = df_metadata[df_metadata["id"] == game_id]

        if not existing_metadata.empty:
            last_scraped_date = existing_metadata.iloc[0]["last_scraped_date"]
            users_rated = existing_metadata.iloc[0]["usersrated"]

            # check percent change of users_rated, and if it rose by more than 5% since last scrape, add to ids_to_scrape
            if users_rated is not None and users_rated > 0:
                percent_change = (row["usersrated"] - users_rated) / users_rated
                if percent_change > 0.05:
                    print(f"Scraping game ID {game_id}: usersrated +{percent_change:.2%}")
                    ids_to_scrape.append(game_id)
                    continue

            if last_scraped_date == get_today_date():
                print(f"Skipping game ID {game_id} since it was already scraped today.")
                continue

        ids_to_scrape.append(str(game_id))
    
    return ids_to_scrape


