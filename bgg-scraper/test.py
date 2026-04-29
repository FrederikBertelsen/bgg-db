import pandas as pd


df_ranks = pd.read_csv("data/ranks/ranks_20260430.csv")

df_ranks = df_ranks[
    (df_ranks['usersrated'] >= 100) & 
    # (df_ranks['yearpublished'] >= 1990) & 
    # (df_ranks['yearpublished'] >= 2025) &
    (df_ranks['is_expansion'] == False)
]

print(len(df_ranks))