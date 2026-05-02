"""
Diagnostic test to analyze similarity scores between two games.
Set game_id_1 and game_id_2 at the top, then run to see component-level breakdown.
"""

import pandas as pd
import ast
import numpy as np
from typing import Any
from boardgame_db import BoardGameDB
import recommender as rec
import recommender_v2 as rec_v2
import recommender_sparse as rec_sp

# ============================================================================
# CONFIGURATION: Set your two game IDs here
# ============================================================================
game_id_1 = "421006"
game_id_2 = "173346"

# ============================================================================

db = BoardGameDB()
df_games = db.df_games


def _ensure_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            parsed = ast.literal_eval(x)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [x]
    try:
        return list(x)
    except Exception:
        return []


def _extract_weight(w: Any) -> float | None:
    if w is None:
        return None
    if isinstance(w, (int, float)):
        return float(w)
    if isinstance(w, dict):
        for key in ("averageweight", "average_weight", "averageWeight", "weight"):
            if key in w:
                try:
                    return float(w[key])
                except Exception:
                    continue
    return None


def analyze_v2_similarity(game_id_1: str, game_id_2: str, df: pd.DataFrame) -> dict:
    """Analyze V2 recommender similarity components between two games."""
    seed_df = df[df['id'] == game_id_1]
    cand_df = df[df['id'] == game_id_2]
    
    if seed_df.shape[0] == 0 or cand_df.shape[0] == 0:
        return {"error": "One or both game IDs not found"}
    
    seed = seed_df.iloc[0]
    cand = cand_df.iloc[0]
    
    # Extract seed properties
    seed_types = set(_ensure_list(seed.get('p_types', [])))
    seed_mech = set(_ensure_list(seed.get('p_mechanics', [])))
    seed_comp = set(_ensure_list(seed.get('p_components', [])))
    seed_themes = set(_ensure_list(seed.get('p_themes', [])))
    seed_weight = _extract_weight(seed.get('weight', None)) or seed.get('average_weight')
    seed_rating = seed.get('rating_average')
    
    # Extract candidate properties
    cand_types = set(_ensure_list(cand.get('p_types', [])))
    cand_mech = set(_ensure_list(cand.get('p_mechanics', [])))
    cand_comp = set(_ensure_list(cand.get('p_components', [])))
    cand_themes = set(_ensure_list(cand.get('p_themes', [])))
    cand_weight = _extract_weight(cand.get('weight', None)) or cand.get('average_weight')
    cand_rating = cand.get('rating_average')
    
    # Compute Jaccard similarities
    def jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 0.0
        inter = len(a & b)
        uni = len(a | b)
        return inter / uni if uni > 0 else 0.0
    
    types_sim = jaccard(seed_types, cand_types)
    mech_sim = jaccard(seed_mech, cand_mech)
    comp_sim = jaccard(seed_comp, cand_comp)
    themes_sim = jaccard(seed_themes, cand_themes)
    
    # Rating bonus
    def rating_bonus(x):
        try:
            r = float(x)
            return max(0.0, min(1.0, r / 10.0))
        except Exception:
            return 0.0
    
    rating_sim = rating_bonus(cand_rating)
    
    # Weight similarity
    def weight_sim(x):
        w = _extract_weight(x) or (x if isinstance(x, (int, float)) else None)
        if seed_weight is None or w is None:
            return 0.0
        return max(0.0, 1.0 - (abs(w - float(seed_weight)) / 4.0))
    
    weight_sim_val = weight_sim(cand.get('weight_average'))
    
    # Default weights from v2
    weights = {"types": 0.3, "mech": 0.33, "comp": 0.25, "themes": 0.0, "rating": 0.02, "weight": 0.1}
    
    total_score = (
        weights['types'] * types_sim
        + weights['mech'] * mech_sim
        + weights['comp'] * comp_sim
        + weights['themes'] * themes_sim
        + weights['rating'] * rating_sim
        + weights['weight'] * weight_sim_val
    )
    
    return {
        "game1_name": seed.get('name'),
        "game2_name": cand.get('name'),
        "components": {
            "types": {"jaccard": types_sim, "weight": weights['types'], "contribution": weights['types'] * types_sim},
            "mechanics": {"jaccard": mech_sim, "weight": weights['mech'], "contribution": weights['mech'] * mech_sim},
            "components": {"jaccard": comp_sim, "weight": weights['comp'], "contribution": weights['comp'] * comp_sim},
            "themes": {"jaccard": themes_sim, "weight": weights['themes'], "contribution": weights['themes'] * themes_sim},
            "rating": {"score": rating_sim, "weight": weights['rating'], "contribution": weights['rating'] * rating_sim},
            "weight": {"similarity": weight_sim_val, "weight": weights['weight'], "contribution": weights['weight'] * weight_sim_val},
        },
        "total_score": total_score,
        "seed_details": {
            "types": list(seed_types),
            "mechanics": list(seed_mech),
            "components": list(seed_comp),
            "themes": list(seed_themes),
            "rating": seed_rating,
            "weight": seed_weight,
        },
        "cand_details": {
            "types": list(cand_types),
            "mechanics": list(cand_mech),
            "components": list(cand_comp),
            "themes": list(cand_themes),
            "rating": cand_rating,
            "weight": cand_weight,
        },
    }


def analyze_original_similarity(game_id_1: str, game_id_2: str, df: pd.DataFrame) -> dict:
    """Analyze original recommender similarity components between two games."""
    seed_df = df[df['id'] == game_id_1]
    cand_df = df[df['id'] == game_id_2]
    
    if seed_df.shape[0] == 0 or cand_df.shape[0] == 0:
        return {"error": "One or both game IDs not found"}
    
    seed = seed_df.iloc[0]
    cand = cand_df.iloc[0]
    
    seed_cats = set(_ensure_list(seed.get('categories', [])))
    seed_mech = set(_ensure_list(seed.get('mechanics', [])))
    seed_weight = _extract_weight(seed.get('weight', None)) or seed.get('average_weight')
    seed_rating = seed.get('rating_average')
    
    cand_cats = set(_ensure_list(cand.get('categories', [])))
    cand_mech = set(_ensure_list(cand.get('mechanics', [])))
    cand_weight = _extract_weight(cand.get('weight', None)) or cand.get('average_weight')
    cand_rating = cand.get('rating_average')
    
    def jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 0.0
        inter = len(a & b)
        uni = len(a | b)
        return inter / uni if uni > 0 else 0.0
    
    cat_sim = jaccard(seed_cats, cand_cats)
    mech_sim = jaccard(seed_mech, cand_mech)
    
    def rating_bonus(x):
        try:
            r = float(x)
            return max(0.0, min(1.0, r / 10.0))
        except Exception:
            return 0.0
    
    rating_sim = rating_bonus(cand_rating)
    
    def weight_sim(x):
        w = _extract_weight(x) or (x if isinstance(x, (int, float)) else None)
        if seed_weight is None or w is None:
            return 0.0
        return max(0.0, 1.0 - (abs(w - float(seed_weight)) / 4.0))
    
    weight_sim_val = weight_sim(cand.get('weight_average'))
    
    weights = {"cat": 0.3, "mech": 0.4, "rating": 0.2, "weight": 0.1}
    
    total_score = (
        weights['cat'] * cat_sim
        + weights['mech'] * mech_sim
        + weights['rating'] * rating_sim
        + weights['weight'] * weight_sim_val
    )
    
    return {
        "game1_name": seed.get('name'),
        "game2_name": cand.get('name'),
        "components": {
            "categories": {"jaccard": cat_sim, "weight": weights['cat'], "contribution": weights['cat'] * cat_sim},
            "mechanics": {"jaccard": mech_sim, "weight": weights['mech'], "contribution": weights['mech'] * mech_sim},
            "rating": {"score": rating_sim, "weight": weights['rating'], "contribution": weights['rating'] * rating_sim},
            "weight": {"similarity": weight_sim_val, "weight": weights['weight'], "contribution": weights['weight'] * weight_sim_val},
        },
        "total_score": total_score,
        "seed_details": {
            "categories": list(seed_cats),
            "mechanics": list(seed_mech),
            "rating": seed_rating,
            "weight": seed_weight,
        },
        "cand_details": {
            "categories": list(cand_cats),
            "mechanics": list(cand_mech),
            "rating": cand_rating,
            "weight": cand_weight,
        },
    }


def analyze_sparse_similarity(game_id_1: str, game_id_2: str, df: pd.DataFrame) -> dict:
    """Analyze sparse recommender similarity components between two games."""
    try:
        # Load or build artifacts
        artifacts = rec_sp.build_recommender_artifacts(df)
        
        seed_idx = artifacts.id_to_index.get(str(game_id_1))
        cand_idx = artifacts.id_to_index.get(str(game_id_2))
        
        if seed_idx is None or cand_idx is None:
            return {"error": "One or both game IDs not found"}
        
        seed_df = df[df['id'] == game_id_1]
        cand_df = df[df['id'] == game_id_2]
        seed = seed_df.iloc[0]
        cand = cand_df.iloc[0]
        
        # Calculate cosine similarity for each block
        components_score = {}
        total_block_score = 0.0
        
        for block_name, matrix in artifacts.block_matrices.items():
            seed_vec = matrix[seed_idx]
            cand_vec = matrix[cand_idx]
            # Cosine similarity: (A · B) / (||A|| ||B||)
            # But since vectors are normalized, it's just the dot product
            sim = seed_vec.dot(cand_vec.T).toarray().ravel()[0]
            sim = float(sim) if not np.isnan(sim) else 0.0
            
            block_weight = rec_sp.DEFAULT_BLOCK_WEIGHTS.get(block_name, 0.0)
            contribution = block_weight * sim
            total_block_score += contribution
            
            components_score[block_name] = {
                "cosine": sim,
                "weight": block_weight,
                "contribution": contribution
            }
        
        # Rating bonus
        seed_rating = float(artifacts.rating_bonus[seed_idx])
        rating_weight = rec_sp.DEFAULT_RATING_WEIGHT
        rating_contribution = rating_weight * seed_rating
        
        components_score["rating_bonus"] = {
            "score": seed_rating,
            "weight": rating_weight,
            "contribution": rating_contribution
        }
        
        # Weight penalty (soft penalty for large gaps)
        seed_weight_val = artifacts.weight_values[seed_idx]
        cand_weight_val = artifacts.weight_values[cand_idx]
        seed_weight_num = None if np.isnan(seed_weight_val) else float(seed_weight_val)
        cand_weight_num = None if np.isnan(cand_weight_val) else float(cand_weight_val)
        
        weight_penalty = 1.0
        if seed_weight_num is not None and cand_weight_num is not None:
            gap = abs(cand_weight_num - seed_weight_num)
            max_gap = rec_sp.DEFAULT_WEIGHT_PENALTY_MAX_GAP
            if gap > max_gap:
                weight_penalty = 1.0 - (rec_sp.DEFAULT_WEIGHT_PENALTY_STRENGTH * (gap - max_gap) / max_gap)
                weight_penalty = max(0.0, weight_penalty)
        
        components_score["weight_penalty"] = {
            "factor": weight_penalty,
            "seed_weight": seed_weight_num,
            "cand_weight": cand_weight_num,
        }
        
        # Total score: (blocks + rating) * penalty
        total_score = (total_block_score + rating_contribution) * weight_penalty
        
        return {
            "game1_name": seed.get('name'),
            "game2_name": cand.get('name'),
            "components": components_score,
            "total_score": total_score,
            "seed_details": {
                "mechanics": list(_ensure_list(seed.get('p_mechanics', []))),
                "types": list(_ensure_list(seed.get('p_types', []))),
                "components": list(_ensure_list(seed.get('p_components', []))),
                "themes": list(_ensure_list(seed.get('p_themes', []))),
                "rating": seed.get('rating_average'),
                "weight": seed_weight_num,
            },
            "cand_details": {
                "mechanics": list(_ensure_list(cand.get('p_mechanics', []))),
                "types": list(_ensure_list(cand.get('p_types', []))),
                "components": list(_ensure_list(cand.get('p_components', []))),
                "themes": list(_ensure_list(cand.get('p_themes', []))),
                "rating": cand.get('rating_average'),
                "weight": cand_weight_num,
            },
        }
    except Exception as e:
        return {"error": f"Error in sparse analysis: {str(e)}"}


def print_analysis(analysis: dict):
    """Pretty print analysis results."""
    if "error" in analysis:
        print(f"  Error: {analysis['error']}")
        return
    
    print(f"\n  {analysis['game1_name']} vs {analysis['game2_name']}")
    print(f"  {'='*70}")
    
    print(f"\n  Seed game ({analysis['game1_name']}):")
    for key, value in analysis['seed_details'].items():
        if isinstance(value, list):
            print(f"    {key}: {value}")
        else:
            print(f"    {key}: {value}")
    
    print(f"\n  Candidate game ({analysis['game2_name']}):")
    for key, value in analysis['cand_details'].items():
        if isinstance(value, list):
            print(f"    {key}: {value}")
        else:
            print(f"    {key}: {value}")
    
    print(f"\n  Component Similarities:")
    for comp_name, comp_data in analysis['components'].items():
        if comp_name == "weight_penalty":
            print(f"    {comp_name:12} - Factor: {comp_data['factor']:.4f} "
                  f"(seed_weight: {comp_data['seed_weight']}, cand_weight: {comp_data['cand_weight']})")
        elif 'jaccard' in comp_data:
            print(f"    {comp_name:12} - Jaccard: {comp_data['jaccard']:.4f}, "
                  f"Weight: {comp_data['weight']:.2f}, Contribution: {comp_data['contribution']:.4f}")
        elif 'cosine' in comp_data:
            print(f"    {comp_name:12} - Cosine: {comp_data['cosine']:.4f}, "
                  f"Weight: {comp_data['weight']:.2f}, Contribution: {comp_data['contribution']:.4f}")
        elif 'score' in comp_data:
            print(f"    {comp_name:12} - Score: {comp_data['score']:.4f}, "
                  f"Weight: {comp_data['weight']:.2f}, Contribution: {comp_data['contribution']:.4f}")
        elif 'similarity' in comp_data:
            print(f"    {comp_name:12} - Similarity: {comp_data['similarity']:.4f}, "
                  f"Weight: {comp_data['weight']:.2f}, Contribution: {comp_data['contribution']:.4f}")
    
    print(f"\n  TOTAL SCORE: {analysis['total_score']:.4f}")
    print(f"  {'='*70}")


# ============================================================================
# RUN ANALYSIS
# ============================================================================

print("\n" + "="*70)
print(f"SIMILARITY ANALYSIS: {game_id_1} vs {game_id_2}")
print("="*70)

print("\n\n[RECOMMENDER V2 - p_ columns with separate weights]")
v2_analysis = analyze_v2_similarity(game_id_1, game_id_2, df_games)
print_analysis(v2_analysis)

print("\n\n[RECOMMENDER ORIGINAL - categories/mechanics]")
orig_analysis = analyze_original_similarity(game_id_1, game_id_2, df_games)
print_analysis(orig_analysis)

# Quick sparse summary (if artifacts are available)
print("\n\n[RECOMMENDER SPARSE - TF-IDF based]")
sparse_analysis = analyze_sparse_similarity(game_id_1, game_id_2, df_games)
print_analysis(sparse_analysis)

print("\n" + "="*70 + "\n")
