import json
import pandas as pd

from extract_details_from_json_column import extract_details
from rankings_dump import filter_rankings
from utils import get_today_date

df_ranks = pd.read_csv(f"data/ranks/ranks_{get_today_date()}.csv")
df_filtered_ranks = filter_rankings(df_ranks)
