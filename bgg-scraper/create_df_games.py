

import json
import math
import re

import pandas as pd

from utils import get_today_date


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
            # Convert from inches to cm (multiply by 2.54)
            l = float(v.get('length') or 0) * 2.54
            w = float(v.get('width') or 0) * 2.54
            d = float(v.get('depth') or 0) * 2.54
        except Exception:
            l = w = d = 0.0
        try:
            weight_lb = float(v.get('weight') or 0)
            weight = weight_lb * 0.45359237
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
        # mean_l = sum(x['l'] for x in best) / len(best)
        # mean_w = sum(x['w'] for x in best) / len(best)
        # mean_d = sum(x['d'] for x in best) / len(best)
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
    # print(f"No dimensions available — using weight-only mean: {mean_wt:.2f} kg")
    return (0.0, round(mean_wt, 2))


def player_count_poll_to_stats(player_count_poll: dict) -> dict:
    """Compact parser producing counts, fractions, score and Wilson LB per player count."""
    if not player_count_poll or not isinstance(player_count_poll, dict):
        return {}

    def wilson(pos: int, n: int, z: float = 1.96) -> float:
        if n <= 0:
            return 0.0
        phat = pos / n
        denom = 1 + (z * z) / n
        num = phat + (z * z) / (2 * n) - z * ((phat * (1 - phat) + (z * z) / (4 * n)) / n) ** 0.5
        return max(0.0, num / denom)

    out = {}

    # New format: {'total_votes': N, 'results': {'1': {'best_rating': X, ...}, ...}}
    if 'results' in player_count_poll and isinstance(player_count_poll.get('results'), dict):
        results = player_count_poll.get('results') or {}
        for k, v in results.items():
            try:
                pc = int(k)
            except Exception:
                pc = k

            if not isinstance(v, dict):
                out[pc] = {'counts': {'best': 0, 'recommended': 0, 'not_recommended': 0}, 'total_votes': 0, 'positive_fraction': 0.0, 'score': 0.0, 'pos_wilson_lb_95': 0.0}
                continue

            try:
                best = int(v.get('best_rating', v.get('best', 0) or 0) or 0)
            except Exception:
                best = 0
            try:
                recommended = int(v.get('recommended_rating', v.get('recommended', 0) or 0) or 0)
            except Exception:
                recommended = 0
            try:
                not_recommended = int(v.get('not_recommended_rating', v.get('not_recommended', 0) or 0) or 0)
            except Exception:
                not_recommended = 0

            counts = {'best': best, 'recommended': recommended, 'not_recommended': not_recommended}
            total_votes = best + recommended + not_recommended

            if total_votes > 0:
                pcts = {t: counts[t] / total_votes for t in counts}
            else:
                pcts = {'best': 0.0, 'recommended': 0.0, 'not_recommended': 0.0}

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

    # Fallback: previous format
    def label(s: str) -> str:
        s = (s or '').lower()
        if 'best' in s:
            return 'best'
        if 'not' in s:
            return 'not_recommended'
        return 'recommended'

    for k, entries in (player_count_poll or {}).items():
        try:
            pc = int(k)
        except Exception:
            pc = k

        counts = {'best': 0, 'recommended': 0, 'not_recommended': 0}

        if not entries or not isinstance(entries, list):
            out[pc] = {'counts': counts, 'total_votes': 0, 'positive_fraction': 0.0, 'score': 0.0, 'pos_wilson_lb_95': 0.0, 'weights': {'best': 1.0, 'recommended': 0.5, 'not_recommended': 0.0}}
            continue

        total_votes = 0
        for e in entries:
            try:
                v = int(float(e.get('votes', 0) or 0))
            except Exception:
                v = 0
            counts[label(e.get('recommendation'))] += v
        total_votes = sum(counts.values())

        pcts = {'best': 0.0, 'recommended': 0.0, 'not_recommended': 0.0}
        if total_votes > 0:
            for t in counts:
                pcts[t] = counts[t] / total_votes
        else:
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


def player_count_poll_to_scores(player_count_poll: dict) -> dict:
    """Compact wrapper that extracts `score` from `player_count_poll_to_stats`.

    Keeps previous behaviour (score in 0..1) while delegating parsing to the
    more featureful `player_count_poll_to_stats` helper.
    """
    stats = player_count_poll_to_stats(player_count_poll)
    return {pc: round(s.get('score', 0.0), 2) for pc, s in stats.items()}

def extract_ranks_and_types(ranks_list: list[dict]) -> tuple[list[dict], list[dict]]:
    ranks = []
    types = []

    for r in ranks_list:
        if not isinstance(r, dict):
            continue
    
        name = r.get('friendlyname', '')

        ranks.append({
            'name': name.replace("Board Game", "Overall").replace("Game ", "").replace("Rank", "").strip(),
            "value": r.get('value')
        })

        type = name.replace("Game Rank", "").replace("Rank", "").strip()
        if type != "Board":
            types.append(type)

    return ranks, types

def extract_versions(versions: list[dict]) -> list[dict]:
    extracted = []
    for v in versions:
        if not isinstance(v, dict):
            continue
            
        language = v.get('language')
        if not language or language.lower() not in ['english', 'danish']:
            continue

        extracted.append({
            'id': v.get('id'),
            'name': v.get('name'),
            'year_published': v.get('yearpublished'),
            'language': language,
            'publisher': v.get('publisher'),
            'thumbnail': v.get('thumbnail'),
            'volume': "{l} x {w} x {d} cm".format(
                l=round(float(v.get('length', 0)*2.54)),
                w=round(float(v.get('width', 0)*2.54)),
                d=round(float(v.get('depth', 0)*2.54)),
            ),
            'weight': "{weight} kg".format(weight=round(float(v.get('weight', 0) * 0.4535924), 1)),
        })    
    return extracted

def extract_expansions(expansions: list[dict]) -> list[dict]:
    extracted = []
    unwanted_terms = ['promo', 'promos', 'promotional', 'user-created', 'fan-made', 'unofficial', 'print and play', 'pnp', 'prototype', 'fan expansion']
    unwanted_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(term) for term in unwanted_terms) + r')\b', re.IGNORECASE)

    for e in expansions:
        if not isinstance(e, dict):
            continue
        
        expansion_name = e.get('name')
        if not expansion_name or unwanted_pattern.search(expansion_name):
            continue

        extracted.append(e)
    return extracted

def create_df_games(json_data: list[dict]) -> pd.DataFrame:
    df_games = pd.DataFrame(json_data)

    df_games.rename(columns={
        'yearpublished': 'year_published',
        'minplayers': 'min_players',
        'maxplayers': 'max_players',
        'playingtime': 'playing_time',
        'minplaytime': 'min_playing_time',
        'maxplaytime': 'max_playing_time',
        'minage': 'min_age',
    }, inplace=True)

    df_games = df_games[(df_games['accessory'] == False) & (df_games['expansion'] == False)]
    df_games.drop(columns=['accessory', 'expansion'], inplace=True)

    # if "Accessory" or "RPG Item" in a rank name, drop row
    df_games = df_games[~df_games['stats'].apply(lambda s: any('Accessory' in r.get('friendlyname', '') or 'RPG Item' in r.get('friendlyname', '') for r in s.get('ranks', []) if isinstance(s, dict) and isinstance(s.get('ranks'), list)))]
    
    df_games[['estimated_volume_cm3', 'estimated_weight_kg']] = df_games['versions'].apply(lambda v: pd.Series(add_estimated_volume_and_weight(v)))
    
    df_games['player_count_scores'] = df_games['suggested_players'].apply(player_count_poll_to_scores)
    df_games.drop(columns=['suggested_players'], inplace=True)


    df_games['rating'] = df_games['stats'].apply(lambda s: s.get('average', 0.0) if isinstance(s, dict) else 0.0)
    df_games['rating_stddev'] = df_games['stats'].apply(lambda s: s.get('stddev', 0.0) if isinstance(s, dict) else 0.0)
    df_games['rating_count'] = df_games['stats'].apply(lambda s: s.get('usersrated', 0) if isinstance(s, dict) else 0)
    df_games['weight'] = df_games['stats'].apply(lambda s: s.get('averageweight', 0.0) if isinstance(s, dict) else 0.0)
    ranks_and_types = df_games['stats'].apply(lambda s: extract_ranks_and_types(s.get('ranks', [])) if isinstance(s, dict) else ([], []))
    df_games[['ranks', 'types']] = pd.DataFrame(ranks_and_types.tolist(), index=df_games.index)
    df_games.drop(columns=['stats'], inplace=True)


    df_games['versions'] = df_games['versions'].apply(extract_versions)
    df_games['expansions'] = df_games['expansions'].apply(extract_expansions)

    # replace newlines with "\n"
    df_games['description'] = df_games['description'].str.replace('\n', '\\n')

    return df_games



if __name__ == "__main__":
    json_file = "downloads/partial_results_20260506.json"
    json_data = json.load(open(json_file, "r", encoding="utf-8"))
    df_games = create_df_games(json_data)

    row_1 = df_games[df_games['id'] == 224517].to_dict(orient='records')[0]
    print("Example row:")
    # pretty print the first row as json
    print(json.dumps(row_1, indent=4))


    # # for each column, print type and number of null values, and 3 example values
    # for column in df_games.columns:
    #     print(f"\n{column}")
    #     dtype = df_games[column].dtype
    #     if dtype == "object":
    #         sample_type = type(df_games[column].dropna().iloc[0]).__name__ if len(df_games[column].dropna()) > 0 else "unknown"
    #         dtype = f"object ({sample_type})"
    #     print(f"    Type: {dtype}")
    #     print(f"    Null values: {df_games[column].isnull().sum()}")
    #     print(f"    Example values: {df_games[column].dropna().head(3).tolist()}")