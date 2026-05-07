import json

import cloudscraper
import pandas as pd

df_final = pd.read_csv("data/final/final_20260506.csv")

df_final['description'] = df_final['description'].str.replace('\n', '\\n')

df_final.to_csv("data/final/final_20260506.csv", index=False)