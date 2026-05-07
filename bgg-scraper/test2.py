import json

import cloudscraper
import pandas as pd

scraper = cloudscraper.create_scraper()

boardgame_id = 167791

url = f"https://api.geekdo.com/api/affiliateads?context=gamemarketplace&objectid={boardgame_id}&objecttype=thing&previewid=0"


print(f"Fetching data for board game ID {boardgame_id} from BGG API...")
response = scraper.get(url)

print(response.status_code)
print()
print(response.text)