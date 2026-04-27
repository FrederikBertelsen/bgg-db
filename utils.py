import re
from datetime import date


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