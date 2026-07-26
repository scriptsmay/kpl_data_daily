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

def generate_ability_timeline(season: str) -> Dict[str, Any]:
    """Generate full ability score timeline for a given season.

    Scans all player-abilities snapshots and builds a time-series with
    absolute values for each historical snapshot, including total_matches,
    overall_rating, 12 ability dimensions, ranks, and position_averages.
    """
    timeline = _build_timeline(season)
    ability_entries = timeline.get("player-abilities", [])

    snapshots = []
    position_averages_nested = None  # 原始按位置分组结构 {pos: {dim: val}}
    player_position = None  # 选手位置（从记录中提取，所有快照应一致）

    for date_str, path in ability_entries:
        try:
            payload = _load_json(path)
        except (json.JSONDecodeError, OSError):
            continue

        data = _unwrap(payload)
        if isinstance(data, list) and data:
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            continue

        # 提取选手位置（取最新非空值，跨快照应一致）
        record_pos = record.get("player_position") or record.get("position")
        if record_pos:
            player_position = record_pos

        total_matches = record.get("total_matches")
        if total_matches is not None:
            try:
                total_matches = int(round(float(total_matches)))
            except (ValueError, TypeError):
                total_matches = 0
        else:
            total_matches = 0

        overall_rating = record.get("overall_rating")
        if overall_rating is not None:
            try:
                overall_rating = float(overall_rating)
            except (ValueError, TypeError):
                overall_rating = None

        overall_rank = record.get("overall_rank")
        if overall_rank is not None:
            try:
                overall_rank = int(round(float(overall_rank)))
            except (ValueError, TypeError):
                overall_rank = None

        position_rank = record.get("position_rank")
        if position_rank is not None:
            try:
                position_rank = int(round(float(position_rank)))
            except (ValueError, TypeError):
                position_rank = None

        abilities = _extract_ability_scores(payload)
        last_updated = record.get("last_updated") or record.get("created_at")

        snapshots.append({
            "date": date_str,
            "last_updated": last_updated,
            "total_matches": total_matches,
            "overall_rating": overall_rating,
            "overall_rank": overall_rank,
            "position_rank": position_rank,
            "abilities": abilities,
        })

        if isinstance(payload, dict) and "position_averages" in payload:
            position_averages_nested = payload["position_averages"]

    # 展平 position_averages：根据选手位置提取对应均值，前端可直接 [dimKey] 取值
    position_averages_flat = None
    if isinstance(position_averages_nested, dict) and player_position:
        nested = position_averages_nested.get(player_position)
        if isinstance(nested, dict):
            position_averages_flat = nested

    reference_date = snapshots[-1]["date"] if snapshots else None
    season_final = _determine_season_final_data(snapshots, season)

    return {
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "reference_date": reference_date,
        "player_position": player_position,
        "position_averages": position_averages_flat,
        "position_averages_by_position": position_averages_nested,
        "season_final_data": season_final,
    }


def _determine_season_final_data(snapshots: List[Dict[str, Any]], season: str) -> str:
    """根据赛程累计局数与最新快照对比，判断赛季决赛数据状态。

    返回值：
    - "complete": 最新快照 total_matches >= 赛程累计小局数
    - "missing": 赛程结束超过 7 天但快照仍未追平
    - "pending": 其他情况（含找不到 schedule.json、赛季进行中等）
    """
    if not snapshots:
        return "pending"

    # schedule.json 可能在当前赛季目录或历史赛季目录
    schedule_paths = [
        DATA_PATH / "derived" / season / "schedule.json",
        DATA_PATH / "seasons" / season / "derived" / "schedule.json",
    ]
    schedule_payload = None
    for p in schedule_paths:
        if p.exists():
            try:
                schedule_payload = _load_json(p)
                break
            except (json.JSONDecodeError, OSError):
                continue

    if not schedule_payload:
        return "pending"

    # 兼容 derived_payload 包装格式与裸 canonical 格式
    if (
        isinstance(schedule_payload, dict)
        and "data" in schedule_payload
        and "schema_version" in schedule_payload
    ):
        schedule_data = schedule_payload["data"]
    else:
        schedule_data = schedule_payload

    if not isinstance(schedule_data, dict):
        return "pending"

    matches = schedule_data.get("matches", [])
    if not isinstance(matches, list) or not matches:
        return "pending"

    # 累计已结束 KSG 比赛的小局数 + 追踪最后一场时间戳
    cumulative_games = 0
    last_match_ts = 0
    for m in matches:
        if not isinstance(m, dict):
            continue
        try:
            status_int = int(m.get("status", 0))
        except (ValueError, TypeError):
            status_int = 0
        # status >= 2 表示已有比分（参考 fetch-schedule.py 的 convert_match 逻辑）
        if status_int >= 2:
            try:
                cumulative_games += int(m.get("score_a", 0)) + int(m.get("score_b", 0))
            except (ValueError, TypeError):
                pass
            try:
                ts = int(m.get("start_ts", 0))
                if ts > last_match_ts:
                    last_match_ts = ts
            except (ValueError, TypeError):
                pass

    if cumulative_games <= 0:
        return "pending"

    latest_snapshot = snapshots[-1]
    try:
        latest_total = int(latest_snapshot.get("total_matches") or 0)
    except (ValueError, TypeError):
        latest_total = 0

    if latest_total >= cumulative_games:
        return "complete"

    # 快照未追平：若最后一场已超过 7 天，视为决赛数据缺失
    if last_match_ts > 0:
        now_ts = datetime.now(timezone.utc).timestamp()
        days_since_last = (now_ts - last_match_ts) / 86400
        if days_since_last > 7:
            return "missing"

    return "pending"


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
