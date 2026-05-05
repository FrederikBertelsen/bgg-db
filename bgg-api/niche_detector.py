"""
Niche detector for board games.

Discovers game niches by clustering games on similarity, then extracting
common properties that define each niche.
"""

from collections import defaultdict
import itertools
import random

import networkx as nx

from recommender_v2 import _ensure_list, load_or_compute_mechanic_importances, score_connection


# Default tunable parameters
DEFAULT_PARAMS = {
    'max_prop_freq': 6000,
    'max_pairs_per_token': 700,
    'edge_cutoff': 0.20,
    'cluster_edge_cutoff': 0.30,
    'min_niche_props': 5,
    'min_games_per_niche': 50,
    'min_coverage': 0.65,
    'max_cluster_size_for_direct_niche': 400,
    'split_edge_multipliers': (1.05, 1.20, 1.35, 1.50),
    'max_global_prop_support': 0.45,
    'min_global_prop_support': 0.002,
    'min_enrichment_ratio': 1.10,
    'max_anchor_global_support': 0.18,
    'max_anchor_count': 180,
    'top_n_niches': 30,
    'niches_max_game_overlap': 0.70,
    'niches_max_prop_overlap': 0.70,
    'connection_weights': {
        'types': 0.25,
        'mech': 0.45,
        'comp': 0.25,
        'themes': 0.0,
        'rating': 0.00,
        'weight': 0.10,
    },
}


def discover_niches(df_games, params=None, verbose=True):
    """
    Discover board game niches from a dataset.
    
    Args:
        df_games: DataFrame with board game data (from BoardGameDB.df_games)
        params: Dict of tunable parameters (merged with DEFAULT_PARAMS)
        verbose: Print progress messages
        
    Returns:
        List of niches, each as tuple:
            (cluster_set, niche_props_dict, selected_props_list, qualifying_games_list)
            where:
            - cluster_set: set of game ids in the niche cluster
            - niche_props_dict: dict of niche properties (e.g. {'type': [...], 'mech': [...], 'comp': [...]})
            - selected_props_list: list of the selected properties that define the niche (e.g. ['type::Strategy', 'mech::Dice Rolling', ...])
            - qualifying_games_list: list of (game_id, matches, coverage, game_name) for games that meet the coverage threshold for the selected properties
    """
    
    # Merge parameters
    p = DEFAULT_PARAMS.copy()
    if params:
        p.update(params)
    
    if verbose:
        print('Building per-game property index...')
    game_props = {}
    for _, row in df_games.iterrows():
        gid = row['id']
        game_props[gid] = {
            'types': set(_ensure_list(row.get('p_types'))),
            'mech': set(_ensure_list(row.get('p_mechanics'))),
            'comp': set(_ensure_list(row.get('p_components'))),
            'row': row,
        }

    if verbose:
        print('Building inverted index (token -> games)')
    token_to_games = defaultdict(list)
    for gid, props in game_props.items():
        for token in props['types'] | props['mech'] | props['comp']:
            token_to_games[token].append(gid)

    if verbose:
        print('Generating candidate pairs from inverted index (skipping very common tokens)...')
    candidate_pairs = set()
    rng = random.Random(42)
    for token, games in token_to_games.items():
        if len(games) < 2 or len(games) > p['max_prop_freq']:
            continue

        max_possible = (len(games) * (len(games) - 1)) // 2
        if max_possible <= p['max_pairs_per_token']:
            pairs_iter = itertools.combinations(games, 2)
        else:
            sampled_pairs = set()
            max_attempts = p['max_pairs_per_token'] * 12
            attempts = 0
            while len(sampled_pairs) < p['max_pairs_per_token'] and attempts < max_attempts:
                a, b = rng.sample(games, 2)
                if a > b:
                    a, b = b, a
                sampled_pairs.add((a, b))
                attempts += 1
            pairs_iter = sampled_pairs

        for a, b in pairs_iter:
            if a < b:
                candidate_pairs.add((a, b))
            else:
                candidate_pairs.add((b, a))

    if verbose:
        print(f'Candidate pairs: {len(candidate_pairs)}')

    if verbose:
        print('Building game_id lookup map for fast scoring...')
    game_id_map = {row['id']: row for _, row in df_games.iterrows()}

    if verbose:
        print('Scoring candidate pairs (using recommender pairwise scorer)...')
    edges = []
    edge_looked_at_count = 0
    mech_weights_cache = load_or_compute_mechanic_importances(df_games, path='data/mechanic_importances.csv')
    for i, (a, b) in enumerate(candidate_pairs):
        if verbose and i > 0 and i % 5000 == 0:
            edge_looked_at_count += 5000
            print(
                f'  Scored {i}/{len(candidate_pairs)} pairs '
                f'({len(edges)} edges kept so far)... '
                f'({100 * edge_looked_at_count / len(candidate_pairs):.1f}%)',
                end='\r',
            )
        try:
            s = score_connection(
                a,
                b,
                df=df_games,
                weights=p['connection_weights'],
                mech_weights=mech_weights_cache,
                game_id_map=game_id_map,
            )
        except Exception:
            continue

        if s['score'] >= p['edge_cutoff']:
            edges.append((a, b, s['score']))

    if verbose:
        print(f'Edges kept (score >= {p["edge_cutoff"]}): {len(edges)}')

    if verbose:
        print('Building game similarity graph...')
    Gg = nx.Graph()
    Gg.add_nodes_from(df_games['id'].tolist())
    for a, b, w in edges:
        Gg.add_edge(a, b, weight=w)
    if verbose:
        print(f'Graph stats: {Gg.number_of_nodes()} nodes, {Gg.number_of_edges()} edges')

    if verbose:
        print(f'Detecting communities from stronger graph (edge >= {p["cluster_edge_cutoff"]})')
    Gc = nx.Graph()
    Gc.add_nodes_from(Gg.nodes())
    Gc.add_edges_from((u, v, d) for u, v, d in Gg.edges(data=True) if d.get('weight', 0.0) >= p['cluster_edge_cutoff'])
    if verbose:
        print(f'Cluster graph stats: {Gc.number_of_nodes()} nodes, {Gc.number_of_edges()} edges')
    game_communities = sorted((set(component) for component in nx.connected_components(Gc)), key=len, reverse=True)
    if verbose:
        print(f'Found {len(game_communities)} game clusters')

    all_tokens_per_game = {}
    for gid, props in game_props.items():
        all_tokens_per_game[gid] = {
            *(f'type::{x}' for x in props['types']),
            *(f'mech::{x}' for x in props['mech']),
            *(f'comp::{x}' for x in props['comp']),
        }

    global_prop_counts = defaultdict(int)
    for tokens in all_tokens_per_game.values():
        for token in tokens:
            global_prop_counts[token] += 1

    token_games_prefixed = defaultdict(set)
    for gid, tokens in all_tokens_per_game.items():
        for token in tokens:
            token_games_prefixed[token].add(gid)

    total_games = max(1, len(df_games))
    global_prop_support = {token: cnt / total_games for token, cnt in global_prop_counts.items()}

    def split_large_cluster(cluster_games: set):
        """Split large components using progressively stronger edge thresholds."""
        clusters = [set(cluster_games)]
        for mult in p['split_edge_multipliers']:
            threshold = p['cluster_edge_cutoff'] * mult
            next_clusters = []
            changed = False
            for cluster in clusters:
                if len(cluster) <= p['max_cluster_size_for_direct_niche']:
                    next_clusters.append(cluster)
                    continue

                subG = Gc.subgraph(cluster).copy()
                weak_edges = [
                    (u, v)
                    for u, v, d in subG.edges(data=True)
                    if d.get('weight', 0.0) < threshold
                ]
                subG.remove_edges_from(weak_edges)

                components = [
                    set(component)
                    for component in nx.connected_components(subG)
                    if len(component) >= p['min_games_per_niche']
                ]
                if len(components) > 1:
                    next_clusters.extend(components)
                    changed = True
                else:
                    next_clusters.append(cluster)

            clusters = next_clusters
            if not changed:
                break
        return clusters

    def extract_niche_from_cluster(cluster_games: set):
        """Given a set of game ids, extract niche properties that are common enough."""
        prop_counts = defaultdict(int)
        for gid in cluster_games:
            for token in all_tokens_per_game[gid]:
                prop_counts[token] += 1

        n = len(cluster_games)
        support = 0.35 if n < 150 else 0.2
        selected = []
        while support >= 0.05:
            candidates = []
            for prop, cnt in prop_counts.items():
                cluster_support = cnt / n
                global_support = global_prop_support.get(prop, 0.0)
                if global_support <= 0:
                    continue
                if cluster_support < support:
                    continue
                if global_support < p['min_global_prop_support'] or global_support > p['max_global_prop_support']:
                    continue

                enrichment = cluster_support / global_support
                if enrichment < p['min_enrichment_ratio']:
                    continue

                rank_score = cluster_support * enrichment
                candidates.append((rank_score, prop))

            candidates.sort(reverse=True)
            selected = [prop for _, prop in candidates[:12]]
            if len(selected) >= p['min_niche_props']:
                break
            support -= 0.1

        niche_props = defaultdict(list)
        for prop in selected:
            cat, name = prop.split('::', 1)
            niche_props[cat].append(name)

        return niche_props, selected

    def add_niche_if_new(source_games: set, niche_props: dict, selected: list, final_list: list):
        """Append niche if not near-duplicate of existing niches."""
        selected_set = set(selected)
        qualifying_games = []
        for gid in source_games:
            token_set = all_tokens_per_game[gid]
            matches = len(token_set & selected_set)
            coverage = matches / len(selected_set) if selected_set else 0.0
            if coverage >= p['min_coverage']:
                qualifying_games.append((gid, matches, coverage, game_props[gid]['row'].get('name', 'Unknown')))

        if len(qualifying_games) < p['min_games_per_niche']:
            return

        new_games = {gid for gid, _, _, _ in qualifying_games}
        for existing in final_list:
            existing_games = {gid for gid, _, _, _ in existing[3]}
            inter = len(new_games & existing_games)
            union = len(new_games | existing_games)
            if union > 0 and (inter / union) >= 0.85:
                return

        final_list.append((source_games, niche_props, selected, qualifying_games))

    if verbose:
        print('\nDeriving niches from clusters...')
    final_niches = []
    candidate_clusters = []
    for cluster in game_communities:
        cluster_set = set(cluster)
        if len(cluster_set) < p['min_games_per_niche']:
            continue
        if len(cluster_set) > p['max_cluster_size_for_direct_niche']:
            candidate_clusters.extend(split_large_cluster(cluster_set))
        else:
            candidate_clusters.append(cluster_set)

    if verbose:
        print(f'Candidate clusters after split: {len(candidate_clusters)}')

    for cluster_set in candidate_clusters:
        niche_props, selected = extract_niche_from_cluster(cluster_set)
        if len(selected) < p['min_niche_props']:
            continue

        selected_set = set(selected)
        qualifying_games = []
        for gid in cluster_set:
            token_set = all_tokens_per_game[gid]
            matches = len(token_set & selected_set)
            coverage = matches / len(selected_set) if selected_set else 0.0
            if coverage >= p['min_coverage']:
                qualifying_games.append((gid, matches, coverage, game_props[gid]['row'].get('name', 'Unknown')))

        if len(qualifying_games) >= p['min_games_per_niche']:
            final_niches.append((cluster_set, niche_props, selected, qualifying_games))

    if len(final_niches) < 5:
        if verbose:
            print('Applying anchor-token fallback to recover broad niches...')
        anchors = [
            token
            for token, sup in sorted(global_prop_support.items(), key=lambda x: x[1], reverse=True)
            if p['min_global_prop_support'] <= sup <= p['max_anchor_global_support']
            and len(token_games_prefixed[token]) >= p['min_games_per_niche']
        ]

        for anchor in anchors[:p['max_anchor_count']]:
            cluster_set = set(token_games_prefixed[anchor])
            if len(cluster_set) < p['min_games_per_niche']:
                continue

            niche_props, selected = extract_niche_from_cluster(cluster_set)
            if anchor not in selected:
                selected = [anchor] + selected
                selected = selected[:12]

            if len(selected) < p['min_niche_props']:
                continue

            add_niche_if_new(cluster_set, niche_props, selected, final_niches)

    def _jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 0.0
        union = len(a | b)
        if union == 0:
            return 0.0
        return len(a & b) / union

    ranked_niches = sorted(
        final_niches,
        key=lambda niche: (-len(niche[3]), -len(niche[2]), -len(niche[0])),
    )

    deduped_niches = []
    for niche in ranked_niches:
        cluster_set, niche_props, selected, qualifying_games = niche
        niche_games = {gid for gid, _, _, _ in qualifying_games}
        niche_props_set = set(selected)

        duplicate = False
        for existing in deduped_niches:
            existing_games = {gid for gid, _, _, _ in existing[3]}
            existing_props = set(existing[2])
            if _jaccard(niche_games, existing_games) >= p['niches_max_game_overlap']:
                duplicate = True
                break
            if _jaccard(niche_props_set, existing_props) >= p['niches_max_prop_overlap']:
                duplicate = True
                break

        if not duplicate:
            deduped_niches.append(niche)

    return deduped_niches
