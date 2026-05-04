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

shopping = df_games['shopping']
    # [{
    #     "seller": "Many Realms",
    #     "seller_country": "US",
    #     "currency": "USD",
    #     "price": "48.99",
    #     "product_url": "https://manyrealms.com/products/die-macher?utm_source=bgg&utm_medium=referral&utm_campaign=bgg_partnership&utm_content=die-macher",
    #     "image_url": "https://cf.geekdo-images.com/uUwLEW5UhEomKuq2x1wmnw__affiliatelogo/img/J7JAflzBDWMzycPYSarc28b7D_Y=/fit-in/0x22/filters:strip_icc()/pic9498173.png",
    #     "price_usd": 48.99,
    #     "price_dkk": 312.56
    # }],
# calculate median price in USD for each boardgame
# ignore none and 0 value rows
df_games = df_games[df_games['shopping'].notna()]
def median_price(shopping):
    prices = [item['price_usd'] for item in shopping if item and item.get('price_usd', 0) > 0]
    if len(prices) == 0:
        return None
    return sum(prices) / len(prices)

df_games['median_price_usd'] = df_games['shopping'].apply(median_price)


# fill na prices with estimate calculated from price per cm3 and rating of other games
ratio = df_games['median_price_usd'] / df_games['estimated_volume_cm3'] / df_games['rating_average']
median_ratio = ratio.median()
def estimate_price(row):
    if pd.notna(row['median_price_usd']):
        return row['median_price_usd']
    if row['estimated_volume_cm3'] > 0 and row['rating_average'] > 0:
        return median_ratio * row['estimated_volume_cm3'] * row['rating_average']
    return None

df_games['estimated_price_usd'] = df_games.apply(estimate_price, axis=1)




# estimated_volume_cm3 / rating_average
# remove none and 0 value rows
df_games = df_games[df_games['estimated_volume_cm3'] > 90]
df_games = df_games[df_games['rating_average'] > 0]
df_games = df_games[df_games['median_price_usd'] < 500]
df_games = df_games[df_games['median_price_usd'] > 5]
# df_games = df_games[df_games['year_published'] > 2015]
df_games = df_games[df_games['estimated_volume_cm3'] <= 3000]

# normalize values
RATING_WEIGHT = 0.5
VOLUME_WEIGHT = 0.25
PRICE_WEIGHT  = 0.25

max_rating = df_games['rating_average'].max()
min_rating = df_games['rating_average'].min()

max_volume = df_games['estimated_volume_cm3'].max()
min_volume = df_games['estimated_volume_cm3'].min()

max_price = df_games['median_price_usd'].max()
min_price = df_games['median_price_usd'].min()

normalized_rating = (df_games['rating_average'] - min_rating) / (max_rating - min_rating)
normalized_volume = (df_games['estimated_volume_cm3'] - min_volume) / (max_volume - min_volume)
normalized_price = (df_games['median_price_usd'] - min_price) / (max_price - min_price)


df_games['value'] = (
    RATING_WEIGHT * normalized_rating +
    VOLUME_WEIGHT * (1 - normalized_volume) +  # lower volume is better
    PRICE_WEIGHT * (1 - normalized_price)  # lower price is better
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
    'median_price_usd': 'price',
    'value': 'value',
    'url': 'url'
}, inplace=True)
# pretty print top 100 games with columns 'rating', 'volume', 'price', 'value' and 'url', without cutting off rows after the first few
print(df_games[['name', 'rating', 'volume', 'price', 'value', 'url']].head(100).to_string(index=False))

print("\n"*3)

specific_game_ids = ['220', '5782', '284083', '324856', '131357', '427593', '277085', '92415', '206915', '223770', '230253']
#find specific games by id and print their name, rating, volume, price and value rank (the placement in the sorted list)
df_specific_games = df_games[df_games['id'].isin(specific_game_ids)]
print(df_specific_games[['name', 'rating', 'volume', 'price', 'value', 'value_rank', 'url']].to_string(index=False))