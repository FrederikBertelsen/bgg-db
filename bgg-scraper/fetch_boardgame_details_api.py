import os
import sys
import json
from time import sleep
import time
from dotenv import load_dotenv
from typing import Any

from bgg_api import fetch_boardgame_details_batch
from utils import get_today_date


def fetch_bgg_api_data(boardgame_ids: list[str]) -> list[dict]:
    WAIT_BETWEEN_REQUESTS = int(os.getenv("WAIT_BETWEEN_REQUESTS", "4"))

    # use a dated partial results file so resumable runs use the same filename
    partial_results_file = f"downloads/partial_results_{get_today_date()}.json"
    results: list[dict[str, Any]] = []
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

    i = 0
    n = 20

    start_time = time.time()
    while i < total_ids:
        batch_ids = boardgame_ids[i:i+n]

        try:
            completed = i
            elapsed = time.time() - start_time
            if completed > 0:
                avg_per_item = elapsed / completed
                remaining = max(0, total_ids - completed)
                est_seconds = avg_per_item * remaining
                est_total_minutes = int(est_seconds // 60)
                est_hours = est_total_minutes // 60
                est_minutes = est_total_minutes % 60
                est_str = f"{est_hours}h {est_minutes}m | {i + 1} -> {remaining}"
            else:
                est_str = "estimating..."
        except Exception:
            est_str = "estimating..."

        print(f"Fetching data for boardgames {i + 1}-{min(i + n, total_ids)}/{total_ids} ( {est_str} )")

        try:
            batch_boardgame_result = fetch_boardgame_details_batch(batch_ids)
        except Exception as e:
            print(f"Error fetching batch {batch_ids}: {e}")
            batch_boardgame_result = []
            i -= n  # step back to retry this batch after the wait

        for batch_index, boardgame_result in enumerate(batch_boardgame_result):
            boardgame_data = boardgame_result.data()

            id = boardgame_data.get("id")
            if id is None or boardgame_data.get("name") is None:
                print(f"Warning: Missing ID or name in API result for boardgame ID {batch_ids[batch_index]}: {id} - {boardgame_data.get('name')}")
                continue

            results.append(boardgame_data)
            existing_ids.add(str(id))

        if i != 0 and i % 100 == 0:
            print(f"Saving partial results to {partial_results_file}...")
            os.makedirs(os.path.dirname(partial_results_file) or "downloads", exist_ok=True)
            with open(partial_results_file, "w", encoding="utf-8") as fh:
                json.dump(results, fh, ensure_ascii=False, indent=2)

        i += n
        if i < total_ids: # only sleep if there are more batches to process
            sleep(WAIT_BETWEEN_REQUESTS)  # add extra sleep after each batch to be polite to the API

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
    data = fetch_bgg_api_data([boardgame_id])
    if not data:
        print("Failed to fetch or parse geekitemPreload JSON.")
        sys.exit(1)

    with open("test.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    print("Saved to test.json")

if __name__ == "__main__":
    main()
