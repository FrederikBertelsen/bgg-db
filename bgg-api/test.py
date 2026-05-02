



from ast import Tuple
import re
import time
from typing import List

import pandas as pd

from boardgame_db import BoardGameDB
from data_conversion import to_json_full


db = BoardGameDB()
df_games = db.df_games

# catan = db.get_game_by_id("13")
# if catan is None:
#     print("Catan not found in database")
#     exit()
    
# print(to_json_full(catan))

# print nunmber of unique values in each of these columns
for col in ['p_mechanics', 'p_types', 'p_components', 'p_themes', 'p_tags']:
    unique_values = set()
    for sublist in df_games[col]:
        unique_values.update(sublist)
    print(f"{col}: {len(unique_values)} unique values")