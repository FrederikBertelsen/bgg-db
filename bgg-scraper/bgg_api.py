import json
import os

from boardgamegeek import BGGClient
from boardgamegeek.objects import BoardGame
from dotenv import load_dotenv


def to_serializable(value):
	if isinstance(value, dict):
		return {key: to_serializable(item) for key, item in value.items()}
	if isinstance(value, (list, tuple, set)):
		return [to_serializable(item) for item in value]
	if hasattr(value, "__dict__"):
		return to_serializable(vars(value))
	return value

load_dotenv()
api_key = os.getenv("BGG_API_KEY", "")
bgg = BGGClient(api_key)

def fetch_boardgame_details(game_id: str) -> BoardGame | None:
	try:
		game = bgg.game(game_id=int(game_id), versions=True)
		return game
	except Exception as e:
		print(f"Error fetching details for game ID {game_id}: {e}")
		return None
	

def fetch_boardgame_details_batch(game_ids: list[str]) -> list[BoardGame]:
	game_ids_int = [int(game_id) for game_id in game_ids]
	try:
		games = bgg.game_list(game_ids_int, versions=True)
		return games
	except Exception as e:
		print(f"Error fetching details for game IDs {game_ids}: {e}")
		return []

if __name__ == "__main__":
	# Example usage:
	game_ids = ["167791", "169786", "342942"]
	details = fetch_boardgame_details_batch(game_ids)
	for game in details:
		print(json.dumps(to_serializable(game.__dict__), indent=4, default=str))