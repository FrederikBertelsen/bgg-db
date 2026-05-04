
from boardgame_db import BoardGameDB


db = BoardGameDB()

# Discover niches
niches = db.get_niches(verbose=True)

# Print results
print(f'\nFound {len(niches)} niches')
print('\nTop niches:')
for ni, niche in enumerate(niches, 1):
    _, niche_props, selected, qualifying_games = niche
    print(f'\nNiche {ni}: {len(qualifying_games)} games, {len(selected)} props')
    print(' Properties:')
    for cat, items in niche_props.items():
        print(f'   {cat}: {sorted(items)[:10]}')
    qualifying_games.sort(key=lambda x: (-x[1], -x[2]))
    print(' Top games:')
    for _, matches, coverage, name in qualifying_games[:10]:
        print(f'   {name} ({matches} matches, {coverage*100:.0f}% coverage)')
