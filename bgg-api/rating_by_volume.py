from ast import Tuple
import json
import re
import time
from typing import List

import pandas as pd

from boardgame_db import BoardGameDB


db = BoardGameDB()
df_games = db.df_games

# print(df_games.columns)
# exit()

df_games = df_games[df_games['rating_count'] > 400]
df_games = df_games[df_games['max_players'] >= 4]
df_games = df_games[df_games['rating_average'] > 6.5]


# remove none and 0 value rows
df_games = df_games[df_games['estimated_volume_cm3'] > 90]
df_games = df_games[df_games['rating_average'] > 0]
# df_games = df_games[df_games['year_published'] > 2015]
df_games = df_games[df_games['estimated_volume_cm3'] <= 4000]

# normalize values
RATING_WEIGHT = 0.60
VOLUME_WEIGHT = 0.40

max_rating = df_games['rating_average'].max()
min_rating = df_games['rating_average'].min()

max_volume = df_games['estimated_volume_cm3'].max()
min_volume = df_games['estimated_volume_cm3'].min()

normalized_rating = (df_games['rating_average'] - min_rating) / (max_rating - min_rating)
normalized_volume = (df_games['estimated_volume_cm3'] - min_volume) / (max_volume - min_volume)

df_games['value'] = (
    RATING_WEIGHT * normalized_rating +
    VOLUME_WEIGHT * (1 - normalized_volume)  # lower volume is better
)

df_games.sort_values(by='value', ascending=False, inplace=True)
# add value_rank column with the rank of the value column
df_games['value_rank'] = df_games['value'].rank(ascending=False)
# print table of result, but last column 'url' should NOT be truncated
pd.set_option('display.max_colwidth', None)

# shorten column names
df_games.rename(columns={
    'rating_average': 'rating',
    'estimated_volume_cm3': 'volume',
    'value': 'value',
    'url': 'url'
}, inplace=True)
# pretty print top 100 games with columns 'rating', 'volume', 'value' and 'url', without cutting off rows after the first few
print(df_games[['name', 'rating', 'volume', 'value', 'url']].head(100).to_string(index=False))

print("\n"*3)

specific_game_ids = ['220', '5782', '284083', '324856', '131357', '427593', '277085', '92415', '206915', '223770', '230253']
#find specific games by id and print their name, rating, volume and value rank (the placement in the sorted list)
df_specific_games = df_games[df_games['id'].isin(specific_game_ids)]
print(df_specific_games[['name', 'rating', 'volume', 'value', 'value_rank', 'url']].to_string(index=False))