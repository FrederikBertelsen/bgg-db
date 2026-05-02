import json

import cloudscraper
import pandas as pd

df_test = pd.read_csv('data/final/final_20260502.csv')

print(df_test[['id','estimated_price_usd','estimated_price_dkk']].head(10))

print(df_test.head())