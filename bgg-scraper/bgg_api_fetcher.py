
# import json
# import os
# import time
# import xml.etree.ElementTree as ET
# from typing import Any

# import requests
# from dotenv import load_dotenv


# load_dotenv()

# # optional BGG API access token (Bearer)
# BGG_API_KEY = os.getenv("BGG_API_KEY")

# BGG_THING_API_URL = "https://boardgamegeek.com/xmlapi2/thing"
# DEFAULT_TIMEOUT = 30
# DEFAULT_RETRIES = 3
# # BGG docs recommend ~5s between requests to avoid throttling
# DEFAULT_RETRY_DELAY = 5.0


# def _coerce_scalar(value: str) -> Any:
# 	value = value.strip()
# 	if not value:
# 		return ""
# 	if value.lower() in {"true", "false"}:
# 		return value.lower() == "true"
# 	try:
# 		integer_value = int(value)
# 		if str(integer_value) == value:
# 			return integer_value
# 	except ValueError:
# 		pass
# 	try:
# 		float_value = float(value)
# 		if str(float_value) == value or "." in value or "e" in value.lower():
# 			return float_value
# 	except ValueError:
# 		pass
# 	return value


# def _xml_element_to_json(element: ET.Element) -> Any:
# 	data: dict[str, Any] = {}

# 	if element.attrib:
# 		data["@attributes"] = dict(element.attrib)

# 	children = list(element)
# 	if children:
# 		grouped_children: dict[str, list[Any]] = {}
# 		for child in children:
# 			grouped_children.setdefault(child.tag, []).append(_xml_element_to_json(child))

# 		for tag_name, values in grouped_children.items():
# 			data[tag_name] = values[0] if len(values) == 1 else values

# 	text = (element.text or "").strip()
# 	if text:
# 		coerced_text = _coerce_scalar(text)
# 		if data:
# 			data["#text"] = coerced_text
# 		else:
# 			return coerced_text

# 	return data



# def fetch_boardgame_details_batch(game_ids: list[str | int]) -> dict[str, Any]:
# 	"""Fetch multiple board game records from BGG and return the raw XML as JSON-compatible data."""
# 	if not game_ids:
# 		raise ValueError("game_ids is required")

# 	if len(game_ids) > 20:
# 		raise ValueError("BGG XMLAPI2 limits requests to a maximum of 20 ids")

# 	params = {
# 		"id": ",".join(str(game_id) for game_id in game_ids),
# 		"versions": "1",
#         "stats": "1",
# 	}

# 	return _fetch_boardgame_details(params)


# def _fetch_boardgame_details(params: dict[str, str]) -> dict[str, Any]:

# 	headers = {
# 		"User-Agent": "bgg-scraper/1.0 (+https://boardgamegeek.com)",
# 		"Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
# 	}

# 	# attach Authorization header when API key is provided
# 	if BGG_API_KEY:
# 		headers["Authorization"] = f"Bearer {BGG_API_KEY}"
# 	else:
# 		print("Warning: No BGG API key provided. Requests may be subject to stricter rate limits.")

# 	last_error: Exception | None = None
# 	for attempt in range(DEFAULT_RETRIES + 1):
# 		try:
# 			response = requests.get(
# 				BGG_THING_API_URL,
# 				params=params,
# 				headers=headers,
# 				timeout=DEFAULT_TIMEOUT,
# 			)

# 			if response.status_code in {202, 503}:
# 				if attempt >= DEFAULT_RETRIES:
# 					response.raise_for_status()
# 				time.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))
# 				continue

# 			response.raise_for_status()
# 			root = ET.fromstring(response.text)
# 			return {root.tag: _xml_element_to_json(root)}
# 		except Exception as exc:
# 			last_error = exc
# 			if attempt >= DEFAULT_RETRIES:
# 				raise
# 			time.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))

# 	if last_error is not None:
# 		raise last_error
# 	raise RuntimeError("unexpected failure while fetching boardgame details")


# if __name__ == "__main__":
# 	data = fetch_boardgame_details_batch([167791])
# 	print(json.dumps(data, indent=2, ensure_ascii=False))