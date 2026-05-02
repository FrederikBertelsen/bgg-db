



from ast import Tuple
import re
import time
from typing import List

import pandas as pd

from boardgame_db import BoardGameDB
import recommender_sparse as rec_sp
import recommender as rec
import recommender_v2 as rec_v2

db = BoardGameDB()
df_games = db.df_games

id = "421006"


# pretty print the game details as json indented.
game = db.get_game_by_id(id) #pandas row (series)
print(len(game['expansions']))