import pandas as pd

from boardgame_db import BoardGameDB
from boardgame_db_io import load_merged_data

df_niches = pd.read_csv("data/niches.csv")

for _, row in df_niches.iterrows():

    print(f"Name: {row['name']}\n   Description: {row['description']}\n  Properties: {row['properties']}\n   Games count: {row['games_count']}\n")