
import json
import math
import numpy as np

import pandas as pd

from utils import get_today_date

def convert_to_usd(price_str: str, currency: str) -> float:
    try:
        price_value = float(price_str)
    except ValueError:
        print(f"Warning: Invalid price '{price_str}' for currency '{currency}' - defaulting to 0.0")
        return 0.0

    if currency == 'USD':
        return price_value
    elif currency == 'EUR':
        return price_value * 1.17
    elif currency == 'GBP':
        return price_value * 1.35
    elif currency == 'CAD':
        return price_value * 0.73
    elif currency == 'CHF':
        return price_value * 1.26
    elif currency == 'AUD':
        return price_value * 0.71
    elif currency == 'DKK':
        return price_value * 0.15
    else:
        raise ValueError(f"Unsupported currency: {currency}")
    
def add_price_conversions(shopping: list[dict]) -> list[dict]:
    # guard: some rows contain NaN/None or non-list values for `shopping`
    if not isinstance(shopping, list):
        return []

    for item in shopping:
        if not isinstance(item, dict):
            print(f"Warning: Expected dict for shopping item but got {type(item)} - skipping: \n{item}\n")
            continue

        currency = item.get('currency')
        if not currency:
            print(f"Warning: Missing currency for item '{item.get('name', '')}' - skipping price conversion")
            continue

        price_str = item.get('price', '0')

        try:
            price_usd = convert_to_usd(price_str, currency)
            item['price_usd'] = round(price_usd, 2)
        except ValueError as e:
            print(f"Error converting price for game '{item.get('name', '')}': {e}")
            item['price_usd'] = 0.0

        item['price_dkk'] = round(item['price_usd'] * 6.38, 2)

    return shopping

def add_estimated_volume_and_weight(versions: list[dict]) -> tuple[float, float]:
    """Estimate average volume (cm^3) and weight (kg) by grouping versions
    with similar dimensions using simple rounding bins.

    This is a compact, readable approximation. Rounds dimensions to the
    nearest 0.5 cm (change `mult` to tune tolerance).
    """
    if not versions:
        return 0.0, 0.0

    # Build a small DataFrame for numeric operations
    try:
        df = pd.DataFrame(versions)
    except Exception:
        return 0.0, 0.0

    for col in ('width', 'depth', 'length', 'weight_kg'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            df[col] = pd.NA

    df = df.dropna(subset=['width', 'depth', 'length'])
    df = df[(df[['width', 'depth', 'length']] > 0).all(axis=1)]
    if df.empty:
        return 0.0, 0.0

    mult = 2  # 0.5 cm bins
    df['w_r'] = (df['width'] * mult).round() / mult
    df['d_r'] = (df['depth'] * mult).round() / mult
    df['l_r'] = (df['length'] * mult).round() / mult

    grp = df.groupby(['w_r', 'd_r', 'l_r'])
    largest_key = grp.size().idxmax()
    g = grp.get_group(largest_key)

    avg_volume = ((g['width'] * 2.54) * (g['depth'] * 2.54) * (g['length'] * 2.54)).mean()
    weights = g['weight_kg']
    avg_weight = weights[weights > 0].mean() if (weights > 0).any() else 0.0

    return float(avg_volume), float(avg_weight)
        


def player_count_poll_to_scores(player_count_poll: dict) -> dict:
    """Compact wrapper that extracts `score` from `player_count_poll_to_stats`.

    Keeps previous behaviour (score in 0..1) while delegating parsing to the
    more featureful `player_count_poll_to_stats` helper.
    """
    stats = player_count_poll_to_stats(player_count_poll)
    return {pc: s.get('score', 0.0) for pc, s in stats.items()}


def player_count_poll_to_stats(player_count_poll: dict) -> dict:
    """Compact parser producing counts, fractions, score and Wilson LB per player count."""
    if not player_count_poll or not isinstance(player_count_poll, dict):
        return {}

    def label(s: str) -> str:
        s = (s or '').lower()
        if 'best' in s:
            return 'best'
        if 'not' in s:
            return 'not_recommended'
        return 'recommended'

    def wilson(pos: int, n: int, z: float = 1.96) -> float:
        if n <= 0:
            return 0.0
        phat = pos / n
        denom = 1 + (z * z) / n
        num = phat + (z * z) / (2 * n) - z * ((phat * (1 - phat) + (z * z) / (4 * n)) / n) ** 0.5
        return max(0.0, num / denom)

    out = {}
    for k, entries in (player_count_poll or {}).items():
        try:
            pc = int(k)
        except Exception:
            pc = k

        counts = {'best': 0, 'recommended': 0, 'not_recommended': 0}
        pcts = {'best': 0.0, 'recommended': 0.0, 'not_recommended': 0.0}

        if not entries or not isinstance(entries, list):
            out[pc] = {'counts': counts, 'pcts': pcts, 'total_votes': 0, 'pos_pct': 0.0, 'score': 0.0, 'pos_wilson_lb_95': 0.0, 'weights': {'best': 1.0, 'recommended': 0.5, 'not_recommended': 0.0}}
            continue

        # Prefer raw vote counts when available (and sum > 0); otherwise fall back to vote_percent.
        # Collect counts first and check total votes.
        total_votes = 0
        for e in entries:
            try:
                v = int(float(e.get('votes', 0) or 0))
            except Exception:
                v = 0
            counts[label(e.get('recommendation'))] += v
        total_votes = sum(counts.values())

        if total_votes > 0:
            for t in counts:
                pcts[t] = counts[t] / total_votes
        else:
            # fall back to vote_percent if present
            if any('vote_percent' in e and e.get('vote_percent') is not None for e in entries):
                for e in entries:
                    try:
                        p = float(e.get('vote_percent', 0) or 0) / 100.0
                    except Exception:
                        p = 0.0
                    pcts[label(e.get('recommendation'))] += p
                s = sum(pcts.values()) or 1.0
                for t in pcts:
                    pcts[t] /= s
                total_votes = 0
            else:
                total_votes = 0

        # positive_fraction = fraction of votes that are Best or Recommended (0..1)
        positive_fraction = pcts['best'] + pcts['recommended']
        score = pcts['best'] + 0.5 * pcts['recommended']
        pos_count = counts['best'] + counts['recommended']
        out[pc] = {
            'counts': counts,
            'total_votes': int(total_votes),
            'positive_fraction': float(positive_fraction),
            'score': float(score),
            'pos_wilson_lb_95': float(wilson(pos_count, total_votes)),
        }

    return out


def create_final_dataset(json_data: list[dict]) -> pd.DataFrame:
    df_details = pd.DataFrame(json_data)

    df_details['types'] = df_details['ranks'].apply(lambda ranks: [r.get('category').replace('Rank', '').strip() for r in (ranks or []) if r.get('category') and r.get('category') != 'Overall Rank'])
    df_details['weight_votes'] = df_details['weight'].apply(lambda w: w.get('votes', 0) if isinstance(w, dict) else 0)
    df_details['weight_average'] = df_details['weight'].apply(lambda w: w.get('averageweight', None) if isinstance(w, dict) else None)
    # df_details['Crowdfunded'] = df_details['families'].apply(lambda cats: any('crowdfund' in str(c).lower() for c in (cats or [])))
    df_details['shopping'] = df_details['shopping'].apply(add_price_conversions)
    df_details[['estimated_volume_cm3', 'estimated_weight_kg']] = df_details['versions'].apply(lambda v: pd.Series(add_estimated_volume_and_weight(v)))
    df_details['player_count_scores'] = df_details['player_count_poll'].apply(player_count_poll_to_scores)
    df_details['player_count_stats'] = df_details['player_count_poll'].apply(player_count_poll_to_stats)
    
    return df_details

if __name__ == "__main__":
    with open(f"downloads/results_{get_today_date()}.json", "r", encoding="utf-8") as fh:
        json_data = json.load(fh)

    df_final = create_final_dataset(json_data)

    print(f"Final dataset: {df_final.shape}")
    print(df_final.head())

    print("\nSaving final data to CSV...")
    # df_final.to_csv(f"data/final/final_{get_today_date()}.csv", index=False)
    # df_final.to_csv(f"data/final.csv", index=False)

    # save one row to as json for testing (pretty print)
    df_final.head(10).to_json(f"data/final_sample.json", orient="records", indent=4)
