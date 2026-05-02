



from ast import Tuple
import re
import time
from typing import List

import pandas as pd

from boardgame_db import BoardGameDB
from data_conversion import to_json_full
from description_recommender import recommend_by_description
from hybrid_recommender import recommend_hybrid


df_games = BoardGameDB().df_games

column_name = 'properties'

series = df_games[column_name].dropna()


from itertools import combinations
from collections import Counter

def find_common_combinations(series: pd.Series, n: int = 3, top_k: int = 20):
    combo_counter = Counter()
    for mech_list in series.dropna():
        combos = combinations(set(mech_list), n)
        combo_counter.update(combos)
        
    return combo_counter.most_common(top_k)


for i in range(1,2):
    print(f"\nTop 10 most common combinations of {i} {column_name}:")
    results = find_common_combinations(series, n=i, top_k=9999999)

    if len(results) == 0:
        print("No combinations found.")
        exit()

    for combo, count in results:
            print(f"{count}: {', '.join(combo)}")

print(f"\nUnique {column_name}: {len(series.explode().unique())}")