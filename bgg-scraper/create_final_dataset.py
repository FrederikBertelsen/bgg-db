
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
    with similar dimensions
    """
    if not isinstance(versions, list) or not versions:
        return (0.0, 0.0)

    vols = []
    weights = []
    for v in versions:
        if not isinstance(v, dict):
            continue
        try:
            l = float(v.get('length') or 0)
            w = float(v.get('width') or 0)
            d = float(v.get('depth') or 0)
        except Exception:
            l = w = d = 0.0
        try:
            weight = float(v.get('weight_kg') or 0)
        except Exception:
            weight = 0.0

        if l > 0 and w > 0 and d > 0:
            vols.append({'l': l, 'w': w, 'd': d, 'vol': l * w * d, 'weight': weight if weight > 0 else None})
        elif weight > 0:
            weights.append(weight)

    if not vols and not weights:
        return (0.0, 0.0)

    if vols:
        # cluster by proximity within tolerance (3 inches = 7.62 cm)
        tol_cm = 3.0 * 2.54
        groups = []  # list of lists of entries
        reps = []    # representative (l,w,d) for each group
        for e in vols:
            assigned = False
            for i, rep in enumerate(reps):
                dist = math.sqrt((e['l'] - rep[0])**2 + (e['w'] - rep[1])**2 + (e['d'] - rep[2])**2)
                if dist <= tol_cm:
                    groups[i].append(e)
                    grp = groups[i]
                    reps[i] = (sum(x['l'] for x in grp)/len(grp), sum(x['w'] for x in grp)/len(grp), sum(x['d'] for x in grp)/len(grp))
                    assigned = True
                    break
            if not assigned:
                groups.append([e])
                reps.append((e['l'], e['w'], e['d']))

        best = max(groups, key=len)
        mean_l = sum(x['l'] for x in best) / len(best)
        mean_w = sum(x['w'] for x in best) / len(best)
        mean_d = sum(x['d'] for x in best) / len(best)
        mean_vol = sum(x['vol'] for x in best) / len(best)
        group_weights = [x['weight'] for x in best if x.get('weight')]
        if group_weights:
            mean_weight = sum(group_weights) / len(group_weights)
        elif weights:
            mean_weight = sum(weights) / len(weights)
        else:
            ratios = [x['weight'] / x['vol'] for x in vols if x.get('weight')]
            mean_weight = (mean_vol * (sum(ratios) / len(ratios))) if ratios else 0.0

        # print chosen group dims and calculations for verification
        # print(f"Chosen group dims (LxWxD): {mean_l:.2f} x {mean_w:.2f} x {mean_d:.2f} (cm)")
        # print(f"Group size: {len(best)}. Estimated volume_cm3: {mean_vol:.2f}. Estimated weight_kg: {mean_weight:.2f}")

        return (round(mean_vol, 2), round(mean_weight, 2))

    # only weights available
    mean_wt = sum(weights) / len(weights)
    print(f"No dimensions available — using weight-only mean: {mean_wt:.2f} kg")
    return (0.0, round(mean_wt, 2))


def player_count_poll_to_scores(player_count_poll: dict) -> dict:
    """Compact wrapper that extracts `score` from `player_count_poll_to_stats`.

    Keeps previous behaviour (score in 0..1) while delegating parsing to the
    more featureful `player_count_poll_to_stats` helper.
    """
    stats = player_count_poll_to_stats(player_count_poll)
    return {pc: round(s.get('score', 0.0), 2) for pc, s in stats.items()}


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

    # remove "rank" from rank categories
    df_details['ranks'] = df_details['ranks'].apply(lambda ranks: [{'category': r.get('category', '').replace('Rank', '').strip(), 'rank': r.get('rank'), 'bayes_average': r.get('bayes_average')} for r in (ranks or []) if r.get('category')])
    df_details['types'] = df_details['ranks'].apply(lambda ranks: [r.get('category') for r in (ranks or []) if r.get('category') and r.get('category') != 'Overall'])
    
    df_details['weight_votes'] = df_details['weight'].apply(lambda w: w.get('votes', 0) if isinstance(w, dict) else 0)
    df_details['weight_average'] = df_details['weight'].apply(lambda w: round(w.get('averageweight', 0.0), 2) if isinstance(w, dict) else None)
    
    # df_details['Crowdfunded'] = df_details['families'].apply(lambda cats: any('crowdfund' in str(c).lower() for c in (cats or [])))
    
    df_details['shopping'] = df_details['shopping'].apply(add_price_conversions)
    df_details[['estimated_volume_cm3', 'estimated_weight_kg']] = df_details['versions'].apply(lambda v: pd.Series(add_estimated_volume_and_weight(v)))
    
    df_details['player_count_scores'] = df_details['player_count_poll'].apply(player_count_poll_to_scores)
    # df_details['player_count_stats'] = df_details['player_count_poll'].apply(player_count_poll_to_stats)
    df_details['PlayerCountBestMin'] = df_details['player_counts'].apply(lambda pc: pc.get('best', [{}])[0].get('min') if isinstance(pc, dict) else None)
    df_details['PlayerCountBestMax'] = df_details['player_counts'].apply(lambda pc: pc.get('best', [{}])[0].get('max') if isinstance(pc, dict) else None)
    df_details['PlayerCountRecommendedMin'] = df_details['player_counts'].apply(lambda pc: pc.get('recommended', [{}])[0].get('min') if isinstance(pc, dict) else None)
    df_details['PlayerCountRecommendedMax'] = df_details['player_counts'].apply(lambda pc: pc.get('recommended', [{}])[0].get('max') if isinstance(pc, dict) else None)
    df_details['PlayerCountVotes'] = df_details['player_counts'].apply(lambda pc: int(pc.get('total_votes', 0)) if isinstance(pc, dict) else 0)

    # remove unwanted columns
    columns_to_drop = ['player_counts', 'weight', 'player_count_poll']
    df_details = df_details.drop(columns=columns_to_drop, errors='ignore')

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
