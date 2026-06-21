"""Compute cross-day trend summaries from historical data snapshots.

Scans dated files in data/ to build time-series for key namespaces,
then computes deltas across 3/7/14/30-day windows.
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.storage.config import DATA_DIR


DATA_PATH = Path(DATA_DIR)
DATE_RE = re.compile(
    r"^(?P<namespace>.+?)\.(?P<season>[A-Z]+[0-9A-Z]*)\.(?P<date>\d{8})\.json$"
)

# Namespaces we track for trends
TREND_NAMESPACES = [
    "player-hero-summary",
    "player-abilities",
    "all-player-stats",
    "player-win-stats",
    "player-lose-stats",
]


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _build_timeline(season: str) -> Dict[str, List[Tuple[str, Path]]]:
    """Scan data/ and build {namespace: [(date_str, path), ...]} for given season."""
    timeline: Dict[str, List[Tuple[str, Path]]] = defaultdict(list)

    for path in sorted(DATA_PATH.glob("*.json")):
        if path.parent.name in {"latest", "derived", "archive", "_reports"}:
            continue
        m = DATE_RE.match(path.name)
        if not m:
            continue
        ns = m.group("namespace")
        s = m.group("season")
        d = m.group("date")
        if ns in TREND_NAMESPACES and s == season:
            timeline[ns].append((d, path))

    # Sort each namespace by date
    for ns in timeline:
        timeline[ns].sort(key=lambda x: x[0])

    return dict(timeline)


def _snapshots_in_window(
    entries: List[Tuple[str, Path]],
    reference_date: datetime,
    days: int,
) -> List[Tuple[str, Path]]:
    """Get snapshots within [reference_date - days, reference_date]."""
    cutoff = reference_date - timedelta(days=days)
    result = []
    for date_str, path in entries:
        d = _parse_date(date_str)
        if cutoff <= d <= reference_date:
            result.append((date_str, path))
    return result


def _extract_hero_names(payload: Any) -> set:
    """Extract hero name set from player-hero-summary data."""
    data = _unwrap(payload)
    if isinstance(data, list):
        return {h.get("hero_name", "") for h in data if h.get("hero_name")}
    return set()


def _extract_ability_scores(payload: Any) -> Dict[str, float]:
    """Extract ability dimension scores from player-abilities data."""
    data = _unwrap(payload)
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        return {}

    dims = [
        "damage_output", "teamfight", "initiation",
        "early_game", "mid_game", "late_game",
        "map_control", "invasion_ability", "support_ability",
        "economy", "tankiness", "durability",
    ]
    scores = {}
    for dim in dims:
        val = record.get(dim)
        if val is not None:
            try:
                scores[dim] = float(val)
            except (ValueError, TypeError):
                pass
    return scores


def _extract_ranking_values(payload: Any) -> Dict[str, float]:
    """Extract ranking indicator values from all-player-stats data."""
    data = _unwrap(payload)
    if isinstance(data, list) and data:
        record = data[0]
    elif isinstance(data, dict):
        record = data
    else:
        return {}

    fields = [
        "damage_per_minute", "damage_taken_per_minute",
        "economy_per_minute", "avg_kill_participation",
        "damage_share", "damage_taken_share",
    ]
    values = {}
    for f in fields:
        val = record.get(f)
        if val is not None:
            try:
                values[f] = float(str(val).replace("%", ""))
            except (ValueError, TypeError):
                pass
    return values


def _compute_hero_pool_trends(
    entries: List[Tuple[str, Path]],
    windows: List[int],
    reference_date: datetime,
) -> Dict[str, Any]:
    """Compute hero pool trend deltas for each time window."""
    trends = {}
    # Get the latest snapshot
    if not entries:
        return trends

    latest_date_str, latest_path = entries[-1]
    latest_data = _load_json(latest_path)
    latest_heroes = _extract_hero_names(latest_data)

    for days in windows:
        snaps = _snapshots_in_window(entries, reference_date, days)
        if len(snaps) < 2:
            trends[f"{days}d"] = {
                "snapshots": len(snaps),
                "hero_count_delta": None,
                "new_heroes": [],
                "dropped_heroes": [],
            }
            continue

        oldest_date_str, oldest_path = snaps[0]
        oldest_data = _load_json(oldest_path)
        oldest_heroes = _extract_hero_names(oldest_data)

        new_heroes = sorted(latest_heroes - oldest_heroes)
        dropped_heroes = sorted(oldest_heroes - latest_heroes)

        trends[f"{days}d"] = {
            "snapshots": len(snaps),
            "date_range": f"{oldest_date_str} ~ {latest_date_str}",
            "hero_count_delta": len(latest_heroes) - len(oldest_heroes),
            "hero_count_latest": len(latest_heroes),
            "hero_count_oldest": len(oldest_heroes),
            "new_heroes": new_heroes,
            "dropped_heroes": dropped_heroes,
        }

    return trends


def _compute_ability_trends(
    entries: List[Tuple[str, Path]],
    windows: List[int],
    reference_date: datetime,
) -> Dict[str, Any]:
    """Compute ability score trend deltas."""
    trends = {}
    if not entries:
        return trends

    latest_date_str, latest_path = entries[-1]
    latest_scores = _extract_ability_scores(_load_json(latest_path))

    for days in windows:
        snaps = _snapshots_in_window(entries, reference_date, days)
        if len(snaps) < 2:
            trends[f"{days}d"] = {"snapshots": len(snaps)}
            continue

        oldest_date_str, oldest_path = snaps[0]
        oldest_scores = _extract_ability_scores(_load_json(oldest_path))

        deltas = {}
        biggest_gain = None
        biggest_drop = None

        for dim in latest_scores:
            if dim in oldest_scores:
                delta = latest_scores[dim] - oldest_scores[dim]
                deltas[dim] = round(delta, 1)
                if biggest_gain is None or delta > biggest_gain[1]:
                    biggest_gain = (dim, delta)
                if biggest_drop is None or delta < biggest_drop[1]:
                    biggest_drop = (dim, delta)

        trends[f"{days}d"] = {
            "snapshots": len(snaps),
            "date_range": f"{oldest_date_str} ~ {latest_date_str}",
            "deltas": deltas,
            "biggest_gain": {biggest_gain[0]: biggest_gain[1]} if biggest_gain else {},
            "biggest_drop": {biggest_drop[0]: biggest_drop[1]} if biggest_drop else {},
        }

    return trends


def _compute_ranking_trends(
    entries: List[Tuple[str, Path]],
    windows: List[int],
    reference_date: datetime,
) -> Dict[str, Any]:
    """Compute ranking value trend deltas."""
    trends = {}
    if not entries:
        return trends

    latest_date_str, latest_path = entries[-1]
    latest_values = _extract_ranking_values(_load_json(latest_path))

    for days in windows:
        snaps = _snapshots_in_window(entries, reference_date, days)
        if len(snaps) < 2:
            trends[f"{days}d"] = {"snapshots": len(snaps)}
            continue

        oldest_date_str, oldest_path = snaps[0]
        oldest_values = _extract_ranking_values(_load_json(oldest_path))

        deltas = {}
        biggest_rise = None
        biggest_drop = None

        for field in latest_values:
            if field in oldest_values and oldest_values[field] != 0:
                delta = latest_values[field] - oldest_values[field]
                pct = round(delta / oldest_values[field] * 100, 1) if oldest_values[field] else 0
                deltas[field] = {"abs": round(delta, 2), "pct": pct}
                if biggest_rise is None or delta > biggest_rise[1]:
                    biggest_rise = (field, delta)
                if biggest_drop is None or delta < biggest_drop[1]:
                    biggest_drop = (field, delta)

        trends[f"{days}d"] = {
            "snapshots": len(snaps),
            "date_range": f"{oldest_date_str} ~ {latest_date_str}",
            "deltas": deltas,
            "biggest_rise": {biggest_rise[0]: biggest_rise[1]} if biggest_rise else {},
            "biggest_drop": {biggest_drop[0]: biggest_drop[1]} if biggest_drop else {},
        }

    return trends


def _detect_anomalies(
    hero_trends: Dict[str, Any],
    ability_trends: Dict[str, Any],
    ranking_trends: Dict[str, Any],
) -> List[str]:
    """Detect anomalies based on trend data."""
    anomalies = []

    # Hero pool shrink
    for window_key, data in hero_trends.items():
        delta = data.get("hero_count_delta")
        if delta is not None and delta < 0:
            latest = data.get("hero_count_latest", 0)
            oldest = data.get("hero_count_oldest", 0)
            if oldest > 0 and abs(delta) / oldest >= 0.3:
                anomalies.append(f"英雄池在 {window_key} 内缩减 {abs(delta)} 个（{oldest} → {latest}）")

    # Ability drop > 10
    for window_key, data in ability_trends.items():
        drop = data.get("biggest_drop", {})
        for dim, val in drop.items():
            if val <= -10:
                anomalies.append(f"能力维度 {dim} 在 {window_key} 内下降 {abs(val)} 分")

    # Ranking drop > 20%
    for window_key, data in ranking_trends.items():
        drop = data.get("biggest_drop", {})
        for field, val in drop.items():
            deltas = data.get("deltas", {}).get(field, {})
            pct = deltas.get("pct", 0)
            if pct <= -20:
                anomalies.append(f"排名指标 {field} 在 {window_key} 内下降 {abs(pct)}%")

    return anomalies


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_trends(season: str) -> Dict[str, Any]:
    """Compute trend summaries for the given season.

    Returns a dict matching the trend-summary.json data structure.
    """
    timeline = _build_timeline(season)

    # Use the latest date across all namespaces as reference
    all_dates = []
    for entries in timeline.values():
        for date_str, _ in entries:
            all_dates.append(date_str)

    if not all_dates:
        return {
            "snapshots_available": 0,
            "trends": {},
            "anomalies": [],
        }

    reference_date = _parse_date(max(all_dates))
    windows = [3, 7, 14, 30]

    hero_timeline = timeline.get("player-hero-summary", [])
    ability_timeline = timeline.get("player-abilities", [])
    ranking_timeline = timeline.get("all-player-stats", [])

    hero_trends = _compute_hero_pool_trends(hero_timeline, windows, reference_date)
    ability_trends = _compute_ability_trends(ability_timeline, windows, reference_date)
    ranking_trends = _compute_ranking_trends(ranking_timeline, windows, reference_date)

    anomalies = _detect_anomalies(hero_trends, ability_trends, ranking_trends)

    total_snapshots = sum(len(entries) for entries in timeline.values())

    return {
        "snapshots_available": total_snapshots,
        "reference_date": reference_date.strftime("%Y%m%d"),
        "trends": {
            "hero_pool": hero_trends,
            "abilities": ability_trends,
            "ranking": ranking_trends,
        },
        "anomalies": anomalies,
    }
