#!/usr/bin/env python3
"""
KPL 赛程采集脚本
调用 KPL 官方 API 获取赛程，转换为 canonical JSON 格式
"""
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

API_BASE = "https://kplshop-op.timi-esports.qq.com/kplow"
TEAM_NAME = "KSG"
PLAYER_NAME = "无言"


def fetch_season_and_teams():
    """获取赛季列表和战队列表"""
    url = f"{API_BASE}/getSeasonAndStageAndTeamList"
    try:
        resp = requests.post(url, json={}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"[fetch-schedule] Season list fetched: {len(data.get('data', []))} items")
        return data.get("data", [])
    except Exception as e:
        print(f"[fetch-schedule] Failed to fetch season list: {e}")
        return []


def find_current_season(seasons):
    """找到当前赛季（is_latest=1 或时间最近的）"""
    for s in seasons:
        if s.get("is_latest") == 1:
            return s
    if seasons:
        return seasons[0]
    return None


def find_team_id(teams, team_name):
    """根据战队名匹配 team_id"""
    for t in teams:
        if t.get("team_name") == team_name or t.get("team_short_name") == team_name:
            return t.get("team_id")
    return None


def fetch_schedule(season_id, team_id):
    """获取指定赛季和战队的赛程"""
    url = f"{API_BASE}/getScheduleList"
    payload = {
        "season_id": season_id,
        "team_id": team_id,
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("data", {}).get("matches", data.get("data", []))
        print(f"[fetch-schedule] Schedule fetched: {len(matches)} matches")
        return matches
    except Exception as e:
        print(f"[fetch-schedule] Failed to fetch schedule: {e}")
        return []


def ts_to_beijing_date(ts):
    """时间戳(秒)转北京时间 MM-DD HH:mm"""
    dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
    return dt.strftime("%m-%d %H:%M")


def convert_match(m, team_name):
    """将原始赛程数据转换为 canonical 格式"""
    status = m.get("schedule_status", 1)
    team_a = m.get("team_a_name", "")
    team_b = m.get("team_b_name", "")
    is_home = team_a == team_name or team_b == team_name

    result = {
        "start_ts": m.get("start_timestamp"),
        "date": ts_to_beijing_date(m.get("start_timestamp", 0)),
        "team_a": team_a,
        "team_b": team_b,
        "is_home": is_home,
        "location": m.get("location_name", ""),
        "stage": m.get("stage_name", ""),
        "bo": m.get("bo_total", 5),
        "status": status,
    }

    if status >= 2:
        result["score_a"] = m.get("team_a_score")
        result["score_b"] = m.get("team_b_score")

    return result


def build_canonical(season_info, team_name, raw_matches):
    """构建 canonical JSON"""
    season_id = season_info.get("season_id", "")
    season_name = season_info.get("season_name", season_id)
    team_id = season_info.get("team_id", "")

    matches = [convert_match(m, team_name) for m in raw_matches]
    matches.sort(key=lambda x: x.get("start_ts", 0))

    return {
        "season_id": season_id,
        "season_name": season_name,
        "team_id": team_id,
        "team_name": team_name,
        "matches": matches,
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

    # 获取赛季和战队列表
    seasons = fetch_season_and_teams()
    if not seasons:
        print("[fetch-schedule] No season data, exit")
        sys.exit(1)

    # 找到当前赛季
    season = find_current_season(seasons)
    if not season:
        print("[fetch-schedule] No current season found, exit")
        sys.exit(1)

    season_id = season.get("season_id", "")
    season_name = season.get("season_name", season_id)
    print(f"[fetch-schedule] Target season: {season_name} ({season_id})")

    # 获取战队列表
    teams = season.get("teams", [])
    team_id = find_team_id(teams, TEAM_NAME)
    if not team_id:
        print(f"[fetch-schedule] Team {TEAM_NAME} not found, trying to find by player name")
        # 备选：从 player-career 数据读取
        career_file = Path("data/latest/player-career-wuyan.json")
        if career_file.exists():
            with open(career_file, "r", encoding="utf-8") as f:
                career = json.load(f)
            latest_team = career.get("latest_team", "") if isinstance(career, dict) else ""
            if latest_team:
                team_id = find_team_id(teams, latest_team)
                print(f"[fetch-schedule] Found team from career data: {latest_team} -> {team_id}")

    if not team_id:
        print(f"[fetch-schedule] Team ID not found for {TEAM_NAME}, exit")
        sys.exit(1)

    # 获取赛程
    raw_matches = fetch_schedule(season_id, team_id)
    if not raw_matches:
        print("[fetch-schedule] No schedule data, exit")
        sys.exit(1)

    # 构建 canonical JSON
    canonical = build_canonical(
        {"season_id": season_id, "season_name": season_name, "team_id": team_id},
        TEAM_NAME,
        raw_matches
    )

    # 保存
    output_dir = Path(f"data/derived/{current_season_id or season_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "schedule.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(canonical, f, ensure_ascii=False, indent=2)

    print(f"[fetch-schedule] Saved to {output_file} ({len(raw_matches)} matches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
