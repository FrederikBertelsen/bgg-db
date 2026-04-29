import json
import re
from datetime import date
from time import sleep

import cloudscraper


def get_today_date():
    return date.today().strftime("%Y%m%d")

def normalize_whitespace_and_newlines(value):
    if isinstance(value, str):
        value = re.sub(r"\r\n?", "\n", value)
        value = value.replace("\n", "\\n")
        value = re.sub(r"[ \t]+", " ", value)
        return value.strip()

    if isinstance(value, dict):
        return {k: normalize_whitespace_and_newlines(v) for k, v in value.items()}

    if isinstance(value, list):
        return [normalize_whitespace_and_newlines(v) for v in value]

    if isinstance(value, tuple):
        return tuple(normalize_whitespace_and_newlines(v) for v in value)

    return value


def fetch_json(scraper: cloudscraper.CloudScraper, url: str, re_pattern: re.Pattern | None = None, headers: dict[str,str] | None = None) -> dict | None:
    error_count = 0
    try:
        while True:
            response = scraper.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch page, status code: {response.status_code}")
                if response.status_code == 403:
                    print("Received 403 Forbidden. This may indicate that Cloudflare is blocking the request.")
                if response.status_code == 429:
                    print("Received 429 Too Many Requests. This may indicate that Cloudflare is rate-limiting the requests.")

                print("Sleeping for 60 seconds before retrying...")
                sleep(60)
                error_count += 1
                if error_count >= 5:
                    print("Too many consecutive errors. Exiting.")
                    return None
            else:
                break

        response_text = response.text
    except Exception as exc:
        print(f"Exception while fetching page '{url}': {exc}")
        return None

    if re_pattern:
        m = re_pattern.search(response_text)
        if m:
            json_str = m.group(1).strip()
        else:
            print(f"No match found for JSON regex.\n{response_text[:1000]}")  # print the first 1000 characters of the HTML for debugging
            return None
    else:
        json_str = response_text.strip()

    try:
        json_data = json.loads(json_str)
        if isinstance(json_data, dict):
            normalized_json_data = normalize_whitespace_and_newlines(json_data)

            if isinstance(normalized_json_data, dict):
                return normalized_json_data

            print(f"Normalized JSON is not a dict: {type(normalized_json_data)}")
            return None
        
        print(f"Fetched JSON is not a dict: {type(json_data)}")
        return None

        
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON: {exc}")
        # save pulled str to file, and exit
        with open("failed_json.json", "w", encoding="utf-8") as f:
            f.write(json_str)
        print("Failed JSON saved to 'failed_json.json' for debugging.")
        exit()
        return None