"""Compute rule-based metrics from derived and latest data.

Reads overview, heroes, abilities, ranking, win-lose derived data and
produces a structured metrics dict used by insights generation and AI prompts.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.analysis.hero_maturity import classify_heroes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    f = _safe_float(value)
    return int(f) if f is not None else None


def _extract_player_record(abilities_data: Any) -> Optional[Dict[str, Any]]:
    """Extract the first player record from abilities derived payload."""
    if not abilities_data:
        return None
    data = abilities_data
    if isinstance(data, dict):
        if "data" in data:
            inner = data["data"]
            if isinstance(inner, list) and inner:
                return inner[0]
            if isinstance(inner, dict):
                return inner
    return None


def _extract_ranking_record(ranking_data: Any) -> Optional[Dict[str, Any]]:
    """Extract the first player record from ranking derived payload."""
    if not ranking_data:
        return None
    data = ranking_data
    if isinstance(data, dict):
        if "data" in data:
            inner = data["data"]
            if isinstance(inner, list) and inner:
                return inner[0]
            if isinstance(inner, dict):
                return inner
    return None


def _extract_position_averages(abilities_data: Any) -> Dict[str, Dict[str, float]]:
    """Extract position_averages from abilities payload."""
    if not abilities_data or not isinstance(abilities_data, dict):
        return {}
    return abilities_data.get("position_averages", {})


# ---------------------------------------------------------------------------
# Sub-metric computations
# ---------------------------------------------------------------------------

ABILITY_DIMS = [
    "damage_output", "teamfight", "initiation",
    "early_game", "mid_game", "late_game",
    "map_control", "invasion_ability", "support_ability",
    "economy", "tankiness", "durability",
]

RANKING_CORE_INDICATORS = [
    ("kda_ratio", "KDA"),
    ("damage_per_minute", "分均伤害"),
    ("damage_taken_per_minute", "分均承伤"),
    ("economy_per_minute", "分均经济"),
    ("avg_kill_participation", "参团率"),
    ("avg_jungle_kills", "野怪击杀"),
]


def compute_hero_pool(
    heroes: Dict[str, Any],
    all_season_heroes: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """Compute hero pool metrics from heroes derived data."""
    summary = heroes.get("summary", [])
    if not summary:
        return {
            "total_heroes": 0,
            "heroes": [],
            "concentration": 0.0,
            "maturity_counts": {},
        }

    # Classify maturity
    classified = classify_heroes(list(summary), all_season_heroes)

    # HHI concentration index
    total_matches = sum(h.get("total_matches", 0) for h in classified)
    if total_matches > 0:
        hhi = sum((h.get("total_matches", 0) / total_matches) ** 2 for h in classified)
    else:
        hhi = 0.0

    # Maturity counts
    maturity_counts: Dict[str, int] = {}
    for h in classified:
        m = h.get("maturity", "trial")
        maturity_counts[m] = maturity_counts.get(m, 0) + 1

    hero_list = []
    for h in classified:
        wr = h.get("win_rate")
        hero_list.append({
            "hero_name": h.get("hero_name", ""),
            "hero_id": h.get("hero_id", ""),
            "total_matches": h.get("total_matches", 0),
            "win_matches": h.get("win_matches", 0),
            "win_rate": _safe_float(str(wr).replace("%", "")) if wr else None,
            "maturity": h.get("maturity", "trial"),
        })

    # Sort by total_matches descending
    hero_list.sort(key=lambda x: x["total_matches"], reverse=True)

    return {
        "total_heroes": len(classified),
        "heroes": hero_list,
        "concentration": round(hhi, 4),
        "maturity_counts": maturity_counts,
        "total_matches": total_matches,
    }


def compute_win_lose_diff(win_lose: Dict[str, Any]) -> Dict[str, Any]:
    """Compute win vs lose differential metrics."""
    win = win_lose.get("win") or {}
    lose = win_lose.get("lose") or {}

    def _get(side: dict, key: str) -> Optional[float]:
        return _safe_float(side.get(key))

    result: Dict[str, Any] = {}

    pairs = [
        ("win_kda", "lose_kda", "avg_kda"),
        ("win_dpm", "lose_dpm", "damage_per_minute"),
        ("win_dtpm", "lose_dtpm", "damage_taken_per_minute"),
        ("win_gold", "lose_gold", "avg_gold"),
        ("win_kill_participation", "lose_kill_participation", "avg_kill_participation"),
        ("win_deaths", "lose_deaths", "avg_deaths"),
        ("win_team_damage_ratio", "lose_team_damage_ratio", "avg_team_damage_ratio"),
        ("win_invasion_duration", "lose_invasion_duration", "avg_invasion_duration"),
    ]

    for win_key, lose_key, src_key in pairs:
        result[win_key] = _get(win, src_key)
        result[lose_key] = _get(lose, src_key)

    # Detect low metrics in losses
    low_in_losses: List[str] = []
    if lose:
        if _get(lose, "avg_kda") is not None and _get(win, "avg_kda") is not None:
            if _get(lose, "avg_kda") < _get(win, "avg_kda") * 0.7:
                low_in_losses.append("KDA 偏低")
        if _get(lose, "damage_per_minute") is not None and _get(win, "damage_per_minute") is not None:
            if _get(lose, "damage_per_minute") < _get(win, "damage_per_minute") * 0.8:
                low_in_losses.append("分均伤害偏低")
        if _get(lose, "avg_deaths") is not None and _get(win, "avg_deaths") is not None:
            if _get(lose, "avg_deaths") > _get(win, "avg_deaths") * 1.3:
                low_in_losses.append("场均死亡偏高")

    result["low_metrics_in_losses"] = low_in_losses
    result["has_lose_data"] = bool(lose)

    return result


def compute_abilities(
    abilities_data: Any,
    prev_abilities_data: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute ability profile metrics and detect volatile dimensions."""
    record = _extract_player_record(abilities_data)
    if not record:
        return {"scores": {}, "ranks": {}, "above_avg": [], "below_avg": [], "volatile": []}

    position_averages = _extract_position_averages(abilities_data)

    # Find the player's position to get the right averages
    player_position = record.get("player_position", "对抗路")
    pos_avg = position_averages.get(player_position, {})

    scores: Dict[str, float] = {}
    ranks: Dict[str, int] = {}
    above_avg: List[str] = []
    below_avg: List[str] = []

    for dim in ABILITY_DIMS:
        val = _safe_float(record.get(dim))
        if val is not None:
            scores[dim] = val
        rank_val = _safe_int(record.get(f"{dim}_position_rank"))
        if rank_val is not None:
            ranks[dim] = rank_val

        avg_val = _safe_float(pos_avg.get(dim))
        if val is not None and avg_val is not None:
            if val > avg_val:
                above_avg.append(dim)
            elif val < avg_val:
                below_avg.append(dim)

    # Detect volatile dimensions by comparing with previous snapshot
    volatile: List[str] = []
    if prev_abilities_data:
        prev_record = _extract_player_record(prev_abilities_data)
        if prev_record:
            for dim in ABILITY_DIMS:
                curr = _safe_float(record.get(dim))
                prev = _safe_float(prev_record.get(dim))
                if curr is not None and prev is not None:
                    delta = abs(curr - prev)
                    if delta >= 5:
                        volatile.append(dim)

    overall_rank = _safe_int(record.get("overall_rank"))
    position_rank = _safe_int(record.get("position_rank"))

    return {
        "scores": scores,
        "ranks": ranks,
        "above_avg": above_avg,
        "below_avg": below_avg,
        "volatile": volatile,
        "overall_rank": overall_rank,
        "position_rank": position_rank,
        "overall_rating": _safe_float(record.get("overall_rating")),
        "player_position": player_position,
    }


def compute_ranking(ranking_data: Any) -> Dict[str, Any]:
    """Compute ranking metrics."""
    record = _extract_ranking_record(ranking_data)
    if not record:
        return {"core_indicators": [], "top_ranked": [], "declining": []}

    core_indicators: List[Dict[str, Any]] = []
    top_ranked: List[str] = []
    declining: List[str] = []

    for field, label in RANKING_CORE_INDICATORS:
        val = _safe_float(record.get(field))
        rank = _safe_int(record.get(f"{field}_rank"))
        if val is not None:
            indicator = {
                "name": label,
                "field": field,
                "value": val,
                "rank": rank,
            }
            core_indicators.append(indicator)

            # Top ranked: rank <= 3 or in top 20%
            if rank is not None and rank <= 3:
                top_ranked.append(label)

    # Also check damage shares
    for field, label in [
        ("damage_share", "伤害占比"),
        ("damage_taken_share", "承伤占比"),
    ]:
        val = record.get(field)
        rank = _safe_int(record.get(f"{field}_rank"))
        if val:
            core_indicators.append({
                "name": label,
                "field": field,
                "value": _safe_float(str(val).replace("%", "")),
                "rank": rank,
            })
            if rank is not None and rank <= 3:
                top_ranked.append(label)

    return {
        "core_indicators": core_indicators,
        "top_ranked": top_ranked,
        "declining": declining,
    }


def compute_team_structure(
    overview: Dict[str, Any],
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute team damage structure from overview data."""
    career = overview.get("career_summary", {})
    season_stats = overview.get("season_stats", [])

    # Match current season by season_id; fall back to last entry for compat
    current_battles = 0
    if season_stats:
        matched = next(
            (s for s in season_stats if s.get("season_id") == season),
            season_stats[-1],
        )
        current_battles = matched.get("battles", 0)

    return {
        "total_career_battles": career.get("total_battles", 0),
        "current_season_battles": current_battles,
        "total_matches": career.get("total_matches", 0),
        "mvp_count": career.get("mvp_count", 0),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_all(
    overview: Dict[str, Any],
    heroes: Dict[str, Any],
    abilities_data: Any,
    ranking_data: Any,
    win_lose: Dict[str, Any],
    all_season_heroes: Optional[Dict[str, Dict[str, int]]] = None,
    prev_abilities_data: Optional[Any] = None,
    season: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute all metrics and return a unified dict.

    Args:
        overview: Derived overview data (data section).
        heroes: Derived heroes data (data section).
        abilities_data: Raw derived abilities payload (with envelope).
        ranking_data: Raw derived ranking payload (with envelope).
        win_lose: Derived win-lose data (data section).
        all_season_heroes: Cross-season hero usage for maturity classification.
        prev_abilities_data: Previous abilities snapshot for volatility detection.
        season: Current season ID for accurate season_stats matching.

    Returns:
        Unified metrics dict with sub-keys: hero_pool, win_lose_diff,
        abilities, ranking, team_structure.
    """
    return {
        "hero_pool": compute_hero_pool(heroes, all_season_heroes),
        "win_lose_diff": compute_win_lose_diff(win_lose),
        "abilities": compute_abilities(abilities_data, prev_abilities_data),
        "ranking": compute_ranking(ranking_data),
        "team_structure": compute_team_structure(overview, season),
    }
