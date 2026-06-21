"""Classify hero usage maturity based on appearance frequency.

Maturity levels:
  core       - Same season >= 5 games, or cross-season with recent usage
  rotation   - 3-4 games in current season
  trial      - 1-2 games in current season
  watch_only - Historical low-frequency or incomplete sample

Win rate is NOT used for classification. It is kept as an attached field only.
"""

from typing import Any, Dict, List, Optional


def _count_cross_season(hero_name: str, all_season_heroes: Dict[str, Dict[str, int]]) -> int:
    """Count how many seasons this hero appeared in (excluding current)."""
    count = 0
    for season_id, heroes in all_season_heroes.items():
        if hero_name in heroes:
            count += 1
    return count


def classify_heroes(
    summary: List[Dict[str, Any]],
    all_season_heroes: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[Dict[str, Any]]:
    """Add maturity classification to each hero in the summary list.

    Args:
        summary: List of hero summary dicts with at least hero_name, total_matches.
        all_season_heroes: Optional dict of {season_id: {hero_name: total_matches}}
            for cross-season detection. Excludes the current season.

    Returns:
        The same list with a 'maturity' field added to each hero dict.
    """
    if all_season_heroes is None:
        all_season_heroes = {}

    for hero in summary:
        total = hero.get("total_matches", 0)
        hero_name = hero.get("hero_name", "")
        cross_seasons = _count_cross_season(hero_name, all_season_heroes)

        if total >= 5:
            maturity = "core"
        elif total >= 3:
            maturity = "rotation"
        elif total >= 1:
            maturity = "trial"
        else:
            maturity = "watch_only"

        hero["maturity"] = maturity

        # Record cross-season usage as supplementary info (does not affect maturity)
        if cross_seasons > 0:
            prior_matches = sum(
                heroes.get(hero_name, 0) for heroes in all_season_heroes.values()
            )
            hero["historical_usage"] = {
                "prior_seasons": cross_seasons,
                "prior_matches": prior_matches,
            }

    return summary


# --- Chinese labels for frontend display ---
MATURITY_LABELS = {
    "core": "核心",
    "rotation": "轮换",
    "trial": "尝试",
    "watch_only": "待观察",
}
