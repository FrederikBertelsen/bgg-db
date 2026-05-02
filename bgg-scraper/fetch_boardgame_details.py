#!/usr/bin/env python3
import os
import sys
import re
import json
from time import sleep
import time
import cloudscraper
from dotenv import load_dotenv
import traceback

from extract_details_from_json import extract_details
from utils import fetch_json, get_today_date

# # File to persist failed boardgame IDs so they can be retried later
# FAILED_IDS_FILE = "data/failed_ids.json"

# def _ensure_failed_ids_dir():
#     dirpath = os.path.dirname(FAILED_IDS_FILE)
#     if dirpath and not os.path.exists(dirpath):
#         os.makedirs(dirpath, exist_ok=True)

# def load_failed_ids() -> set:
#     _ensure_failed_ids_dir()
#     try:
#         if os.path.exists(FAILED_IDS_FILE):
#             with open(FAILED_IDS_FILE, "r", encoding="utf-8") as fh:
#                 data = json.load(fh)
#                 if isinstance(data, list):
#                     return set(str(x) for x in data)
#     except Exception:
#         pass
#     return set()

# def save_failed_ids(failed_ids: set) -> None:
#     _ensure_failed_ids_dir()
#     try:
#         with open(FAILED_IDS_FILE, "w", encoding="utf-8") as fh:
#             json.dump(sorted(list(failed_ids)), fh, ensure_ascii=False, indent=2)
#     except Exception as exc:
#         print(f"Warning: failed to save failed IDs file: {exc}")

# def add_failed_id(failed_ids: set, boardgame_id: str) -> None:
#     if boardgame_id not in failed_ids:
#         failed_ids.add(boardgame_id)
#         save_failed_ids(failed_ids)

# def remove_failed_id(failed_ids: set, boardgame_id: str) -> None:
#     if boardgame_id in failed_ids:
#         failed_ids.discard(boardgame_id)
#         save_failed_ids(failed_ids)


def pull_geek_item_preload_json(scraper: cloudscraper.CloudScraper, boardgame_id: str) -> dict | None:
    url = f"https://boardgamegeek.com/boardgame/{boardgame_id}"

    line_re = re.compile(r"\s*GEEK\.geekitemPreload = (.*}});\s*$", re.MULTILINE)
    
    json_data = fetch_json(scraper, url, line_re)
    if json_data:
        if "item" in json_data:
            return json_data.get("item", {})
        else:
            print(f"Fetched JSON does not contain 'item' key for boardgame ID {boardgame_id}.")
            return None
    
    print(f"Failed to fetch or parse geekitemPreload JSON for boardgame ID {boardgame_id}.")
    return None

def pull_versions_json(scraper: cloudscraper.CloudScraper, boardgame_id: str) -> list[dict] | None:
    versions_url = f"https://api.geekdo.com/api/geekitem/linkeditems?ajax=1&linkdata_index=boardgameversion&nosession=1&objectid={boardgame_id}&objecttype=thing&pageid=1&showcount=25&sort=yearpublished&subtype=boardgameversion"

    versions_json = fetch_json(scraper, versions_url)
    if not versions_json:
        print(f"Failed to fetch or parse version JSON for boardgame ID {boardgame_id}.")
        return None
    
    processed_versions: list[dict] = []
    try:
        items = versions_json.get("items", [])
        if not isinstance(items, list):
            print(f"Unexpected format for versions JSON for boardgame ID {boardgame_id}: 'linkeditems' is not a list.")
            return None

        for version in items:
            name = version.get("versionname")
            year_published = version.get("yearpublished")
            href = version.get("href")
            clean_href = href.replace("\\/", "/") if href else None
            url = f"https://boardgamegeek.com{clean_href}" if clean_href else None

            original_image = version.get("images", {}).get("original")
            image_url = original_image.replace("\\/", "/") if original_image else None

            weight_kg = version.get("weight")
            width = version.get("width")
            depth = version.get("depth")
            length = version.get("length")

            processed_versions.append({
                "name": name,
                "year_published": year_published,
                "weight_kg": float(weight_kg) * 0.45359237 if weight_kg else None,
                "width": float(width) * 2.54 if width else None,
                "depth": float(depth) * 2.54 if depth else None,
                "length": float(length) * 2.54 if length else None,
                "url": url,
                "image_url": image_url,
            })

        # print(f"Fetched {len(processed_versions)} versions")
        return processed_versions
    except Exception as exc:
        print(f"Exception while processing version JSON for boardgame ID {boardgame_id}: {exc}")
        traceback.print_exc()
        return None
    
def pull_shopping_json(scraper: cloudscraper.CloudScraper, boardgame_id: str) -> list[dict] | None:
    shopping_url = f"https://api.geekdo.com/api/affiliateads?context=gamemarketplace&objectid={boardgame_id}&objecttype=thing&previewid=0"

    shopping_json = fetch_json(scraper, shopping_url)
    if not shopping_json:
        print(f"Failed to fetch or parse shopping JSON for boardgame ID {boardgame_id}.")
        return None

    sellers = []
    try:
        shopping_data = shopping_json.get("affiliate_ads", [])
        if isinstance(shopping_data, list):
            for ad in shopping_data:
                seller = ad.get("advertiser").get("name")
                seller_country = ad.get("advertiser").get("country")
                currency = ad.get("currency")
                price = ad.get("price")
                product_url = ad.get("url")
                image_url = ad.get("advertiser").get("imageSets").get("affiliatelogo").get("src")

                sellers.append({
                    "seller": seller,
                    "seller_country": seller_country,
                    "currency": currency,
                    "price": price,
                    "product_url": product_url,
                    "image_url": image_url,
                })
            # print(f"Fetched {len(sellers)} sellers")
            return sellers
        else:
            print(f"Unexpected format for shopping JSON for boardgame ID {boardgame_id}: 'affiliateads' is not a list.")
            return None
    except Exception as exc:
        print(f"Exception while processing shopping JSON for boardgame ID {boardgame_id}: {exc}")
        traceback.print_exc()
        return None

def pull_player_count_poll_json(scraper: cloudscraper.CloudScraper, boardgame_id: str) -> dict | None:
    try:
        poll_url = f"https://boardgamegeek.com/geekitempoll.php?action=view&itempolltype=numplayers&objectid={boardgame_id}&objecttype=thing&ajax=1"
        headers = {
            "accept": "application/json, text/plain, /",
            "referer": f"https://boardgamegeek.com/boardgame/{boardgame_id}",
        }
        poll_data = fetch_json(scraper, poll_url, headers=headers)

        if not poll_data or "poll" not in poll_data:
            print(f"Failed to fetch or parse player count poll JSON for boardgame ID {boardgame_id}.")
            return None
        
        poll_id = poll_data["poll"]["pollid"]

        poll_results_url = f"https://boardgamegeek.com/geekpoll.php?action=results&pollid={poll_id}"
        poll_results_data = fetch_json(scraper, poll_results_url, headers=headers)
        if not poll_results_data or "pollquestions" not in poll_results_data:
            print(f"Failed to fetch or parse player count poll results JSON for boardgame ID {boardgame_id}.")
            return None
        
        poll_questions = poll_results_data["pollquestions"]

        results = [
            dict(result)
            for result in poll_questions[0]["results"]["results"]
            if result.get("votes", "0") != "0"
        ]

        player_count_dict = {}

        for result in results:
            num_players = result.get("rowbody")
            votes = result.get("votes")
            recommendation = result.get("columnbody")
            vote_percent = result.get("percent")

            # accumulate multiple entries for the same player count
            entry = {
                "votes": votes,
                "recommendation": recommendation,
                "vote_percent": vote_percent,
            }
            if num_players is None:
                print(f"Warning: Missing num_players in poll result for boardgame ID {boardgame_id}: {result}")
                continue

            player_count_dict.setdefault(num_players, []).append(entry)

        # print(f"Fetched poll data for {len(player_count_dict)} player counts")
        return player_count_dict
    except Exception as exc:
        print(f"Failed to fetch or parse player count poll JSON for boardgame ID {boardgame_id}: {exc}")
        traceback.print_exc()
        return None

def pull_weight_poll_json(scraper: cloudscraper.CloudScraper, boardgame_id: str) -> dict | None:
    poll_url = f"https://boardgamegeek.com/geekitempoll.php?action=view&itempolltype=boardgameweight&objectid={boardgame_id}&objecttype=thing&ajax=1"
    headers = {
        "accept": "application/json, text/plain, /",
        "referer": f"https://boardgamegeek.com/boardgame/{boardgame_id}",
    }

    try:
        poll_data = fetch_json(scraper, poll_url, headers=headers)
        if not poll_data or "poll" not in poll_data:
            print(f"Failed to fetch or parse player count poll JSON for boardgame ID {boardgame_id}.")
            return None
        
        poll_id = poll_data["poll"]["pollid"]

        poll_results_url = f"https://boardgamegeek.com/geekpoll.php?action=results&pollid={poll_id}"
        poll_results_data = fetch_json(scraper, poll_results_url, headers=headers)
        if not poll_results_data or "pollquestions" not in poll_results_data:
            print(f"Failed to fetch or parse player count poll results JSON for boardgame ID {boardgame_id}.")
            return None
        
        poll_questions = poll_results_data["pollquestions"]
        results = [
            dict(result)
            for result in poll_questions[0]["results"]["results"]
            if result.get("votes", 0)
        ]

        weight_dict = {}
        for result in results:
            weight = result.get("columnbody")
            weight_match = re.search(r"([\d.]+)", weight) if weight else None
            weight = weight_match.group(1) if weight_match else None

            votes = result.get("votes")
            vote_percent = result.get("percent")

            entry = {
                "votes": votes,
                "vote_percent": vote_percent,
            }
            if weight is None:
                print(f"Warning: Missing weight in poll result for boardgame ID {boardgame_id}: {result}")
                continue

            weight_dict.setdefault(weight, []).append(entry)
        
        # print(f"Fetched poll data for {len(weight_dict)} weight categories")
        return weight_dict
        
    except Exception as exc:
        print(f"Failed to fetch or parse weight poll JSON for boardgame ID {boardgame_id}: {exc}")
        traceback.print_exc()


    return None

def pull_bgg_json_data(boardgame_ids: list[str]) -> list[dict]:
    scraper = cloudscraper.create_scraper()

    WAIT_BETWEEN_PAGES = int(os.getenv("WAIT_BETWEEN_PAGES", "2"))

    # use a dated partial results file so resumable runs use the same filename
    partial_results_file = f"downloads/partial_results_{get_today_date()}.json"
    results: list[dict] = []
    existing_ids: set[str] = set()
    if os.path.exists(partial_results_file):
        try:
            with open(partial_results_file, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if isinstance(loaded, list):
                    results = loaded
                    existing_ids = set(str(entry.get("id")) for entry in results if isinstance(entry, dict) and entry.get("id") is not None)
                    # print(f"Loaded {len(results)} partial results from {partial_results_file}")
                else:
                    print(f"Partial results file {partial_results_file} does not contain a list; ignoring.")
        except Exception as exc:
            print(f"Warning: failed to load partial results from {partial_results_file}: {exc}")


    # remove existing_ids from boardgame_ids to avoid processing them again
    boardgame_ids = [bg_id for bg_id in boardgame_ids if str(bg_id) not in existing_ids]
    
    total_ids = len(boardgame_ids)
    
    print(f"\nProcessing {total_ids} boardgame IDs after excluding {len(existing_ids)} already in partial results\n")

    start_time = time.time()
    for i, boardgame_id in enumerate(boardgame_ids):
        try:
            try:
                completed = i
                elapsed = time.time() - start_time
                if completed > 0:
                    avg_per_item = elapsed / completed
                    remaining = max(0, total_ids - completed)
                    est_seconds = avg_per_item * remaining
                    est_hours = est_seconds / 3600
                    est_str = f"{est_hours:.2f}h | {i + 1} -> {remaining}"
                else:
                    est_str = "estimating..."
            except Exception:
                est_str = "estimating..."

            print(f"Fetching data for boardgame ID {boardgame_id} ( {est_str} )")

            sleep(WAIT_BETWEEN_PAGES)
            # print(f"Fetching geekitemPreload...")
            preload_json = pull_geek_item_preload_json(scraper, boardgame_id)
            
            if preload_json:
                # print("Cleaning and normalizing geekitemPreload data...")
                cleaned_data = extract_details(preload_json)
                
                sleep(WAIT_BETWEEN_PAGES)
                # print(f"Fetching versions data...")
                version_data = pull_versions_json(scraper, boardgame_id)
                if version_data:
                    cleaned_data["versions"] = version_data
                else:
                    cleaned_data["versions"] = []

                # sleep(WAIT_BETWEEN_PAGES)
                # print(f"Fetching shopping data...")
                shopping_data = pull_shopping_json(scraper, boardgame_id)
                if shopping_data:
                    cleaned_data["shopping"] = shopping_data
                else:
                    cleaned_data["shopping"] = []
                
                sleep(WAIT_BETWEEN_PAGES)
                # print(f"Fetching player count poll data...")
                player_count_poll_data = pull_player_count_poll_json(scraper, boardgame_id)
                if player_count_poll_data:
                    cleaned_data["player_count_poll"] = player_count_poll_data
                else:
                    cleaned_data["player_count_poll"] = {}
                
                # sleep(WAIT_BETWEEN_PAGES)
                # print(f"Fetching weight poll data...")
                # weight_poll_data = pull_weight_poll_json(scraper, boardgame_id)
                # if weight_poll_data:
                #     cleaned_data["weight_poll"] = weight_poll_data

                results.append(cleaned_data)
                # record id to avoid duplicates in this run
                try:
                    cid = cleaned_data.get("id")
                    existing_ids.add(str(cid) if cid is not None else str(boardgame_id))
                except Exception:
                    pass
            else:
                print(f"Failed to fetch or parse data for boardgame ID {boardgame_id}.")

        except Exception as exc:
            print(f"Exception while fetching data for boardgame ID {boardgame_id}: {exc}")    
            traceback.print_exc()
        
        if (i + 1) % 100 == 0:
            print(f"Saving partial results to {partial_results_file}...")
            os.makedirs(os.path.dirname(partial_results_file) or "downloads", exist_ok=True)
            with open(partial_results_file, "w", encoding="utf-8") as fh:
                json.dump(results, fh, ensure_ascii=False, indent=2)

        
    # save data
    # ensure downloads dir exists
    final_dir = os.path.dirname(partial_results_file)
    if final_dir and not os.path.exists(final_dir):
        os.makedirs(final_dir, exist_ok=True)
    with open(f"downloads/results_{get_today_date()}.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    # also update the partial results file with the full results so it can be resumed if interrupted later
    try:
        with open(partial_results_file, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    return results


def main():
    load_dotenv()
    boardgame_id = "342942"
    data = pull_bgg_json_data([boardgame_id])
    if not data:
        print("Failed to fetch or parse geekitemPreload JSON.")
        sys.exit(1)


    with open("test.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    print("Saved to test.json")

if __name__ == "__main__":
    main()
