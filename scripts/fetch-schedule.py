#!/usr/bin/env python3
"""
KPL 赛程采集脚本
调用 KPL 官方 API 获取赛程，转换为 canonical JSON 格式
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

API_BASE = "https://kplshop-op.timi-esports.qq.com/kplow"
TEAM_NAME = "KSG"
PLAYER_NAME = "无言"


def fetch_seasons():
    """获取赛季列表"""
    url = f"{API_BASE}/getSeasonAndStageAndTeamList"
    try:
        resp = requests.post(url, json={}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        seasons = data.get("data", {}).get("seasons", [])
        print(f"[fetch-schedule] Season list fetched: {len(seasons)} items")
        return seasons
    except Exception as e:
        print(f"[fetch-schedule] Failed to fetch season list: {e}")
        return []


def find_current_season(seasons):
    """找到当前赛季（is_cur_season=1）"""
    if not isinstance(seasons, list):
        print(f"[fetch-schedule] Warning: seasons is not a list ({type(seasons).__name__})")
        return None
    for s in seasons:
        if isinstance(s, dict) and s.get("is_cur_season") == 1:
            return s
    if seasons and isinstance(seasons[0], dict):
        return seasons[0]
    return None


def fetch_schedule(season_id):
    """获取指定赛季的全部赛程"""
    url = f"{API_BASE}/getScheduleList"
    payload = {"season_id": season_id}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("data", {}).get("list", [])
        print(f"[fetch-schedule] Schedule fetched: {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"[fetch-schedule] Failed to fetch schedule: {e}")
        return []


def ts_to_beijing_date(ts_str):
    """时间戳(秒)转北京时间 MM-DD HH:mm"""
    try:
        ts = int(ts_str)
        dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
        return dt.strftime("%m-%d %H:%M")
    except (ValueError, TypeError):
        return ""


def convert_match(m):
    """将原始赛程数据转换为 canonical 格式"""
    status = int(m.get("schedule_status", 1))
    team_a = m.get("team_a_name", "")
    team_b = m.get("team_b_name", "")
    is_ksg = TEAM_NAME in team_a or TEAM_NAME in team_b

    result = {
        "schedule_id": m.get("scheduleid", ""),
        "start_ts": int(m.get("start_timestamp", 0)),
        "date": ts_to_beijing_date(m.get("start_timestamp")),
        "team_a": team_a,
        "team_b": team_b,
        "is_ksg": is_ksg,
        "location": m.get("location_name", ""),
        "stage": m.get("stage_name", ""),
        "bo": int(m.get("bo_total", 5)),
        "status": status,
    }

    if status >= 2:
        result["score_a"] = int(m.get("team_a_score", 0))
        result["score_b"] = int(m.get("team_b_score", 0))

    return result


def build_canonical(season_id, season_name, raw_matches):
    """构建 canonical JSON，只保留 KSG 相关比赛"""
    all_matches = [convert_match(m) for m in raw_matches]
    all_matches.sort(key=lambda x: x.get("start_ts", 0))

    # 过滤 KSG 相关比赛
    ksg_matches = [m for m in all_matches if m["is_ksg"]]

    return {
        "season_id": season_id,
        "season_name": season_name,
        "team_name": TEAM_NAME,
        "total_matches": len(all_matches),
        "ksg_matches": len(ksg_matches),
        "matches": ksg_matches,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_status": "ok"
    }


def main():
    # 读取当前赛季信息
    current_season_file = Path("data/latest/current-season.json")
    if current_season_file.exists():
        with open(current_season_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        current_season_id = meta.get("current", "")
        print(f"[fetch-schedule] Current season from meta: {current_season_id}")
    else:
        current_season_id = None
        print("[fetch-schedule] current-season.json not found, will detect from API")

    # 获取赛季列表
    seasons = fetch_seasons()
    if not seasons:
        print("[fetch-schedule] No season data, exit")
        sys.exit(1)

    # 找到当前赛季
    season = find_current_season(seasons)
    if not season:
        print("[fetch-schedule] No current season found, exit")
        sys.exit(1)

    season_id = season.get("seasonid", "")
    season_name = season.get("season_name", season_id)
    print(f"[fetch-schedule] Target season: {season_name} ({season_id})")

    # 获取全部赛程
    raw_matches = fetch_schedule(season_id)
    if not raw_matches:
        print("[fetch-schedule] No schedule data, exit")
        sys.exit(1)

    # 构建 canonical JSON
    canonical = build_canonical(season_id, season_name, raw_matches)

    # 保存
    output_dir = Path(f"data/derived/{current_season_id or season_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "schedule.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(canonical, f, ensure_ascii=False, indent=2)

    print(f"[fetch-schedule] Saved to {output_file} ({canonical['ksg_matches']} KSG matches / {canonical['total_matches']} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
