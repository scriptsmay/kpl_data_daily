#!/usr/bin/env python3
"""
KPL 数据采集工具

每日定时抓取配置中的 API 接口数据
- 固定 API: 保存为 {命名空间}{赛季 ID}.json
- 每日更新 API: 保存为 {命名空间}{赛季 ID}.{日期}.json
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from src.crawler.config import (
    APIS,
    CURRENT_SEASON,
    API_PLAYER_HERO_BATTLES,
    DATE_FORMAT,
    TARGET_PLAYER,
    TARGET_TEAM,
)
from src.crawler.fetcher import KPLCrawler
from src.storage.saver import KPLStorage


def get_latest_season(crawler: KPLCrawler) -> Optional[Dict]:
    """获取最新赛季信息"""
    url = "http://47.102.210.150:5006/seasons/list?project=KPL"
    data = crawler.fetch(url)

    if not data:
        return None

    # 找到 is_latest=1 的赛季
    for season in data:
        if season.get("is_latest") == 1:
            season_id = season.get("tournament_id")
            if not season_id:
                continue
            # 获取详细赛季信息（包含开始/结束日期）
            season_detail_url = f"http://47.102.210.150:5006/season/{season_id}"
            season_detail = crawler.fetch(season_detail_url)
            return season_detail

    return None


def is_season_active(season: Dict) -> bool:
    """检查赛季是否在有效期内（包括结束日期的三天内都需要更新）"""
    if not season:
        return False

    start_date_str = season.get("start_date")
    end_date_str = season.get("end_date")

    if not start_date_str or not end_date_str:
        return True  # 没有日期信息，默认执行

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    today = datetime.now()

    # 结束日期的三天内
    end_date_plus_one = end_date + timedelta(days=3)

    return start_date <= today <= end_date_plus_one


def filter_player_data(data: Any, player_name: str) -> Union[dict, list]:
    """
    从批量数据中筛选指定选手的数组集合
    """
    name_fields = ["player_name", "playerName", "name", "player", "displayName"]
    
    # 1. 统一提取待处理的列表
    source_list = []
    is_wrapped_dict = False
    
    if isinstance(data, dict) and "data" in data:
        source_list = data["data"] if isinstance(data["data"], list) else []
        is_wrapped_dict = True
    elif isinstance(data, list):
        source_list = data
    else:
        return data

    # 2. 执行筛选 (收集所有匹配项)
    filtered_results = []
    for item in source_list:
        if isinstance(item, dict):
            # 检查是否有任何字段匹配
            if any(player_name in str(item.get(field, "")) for field in name_fields):
                filtered_results.append(item)

    # 3. 根据原始格式返回结果
    if is_wrapped_dict:
        result = data.copy()
        result["data"] = filtered_results
        return result
    
    return filtered_results


def get_hero_list_from_career(storage: KPLStorage) -> list:
    """从已保存的职业生涯数据中提取英雄列表"""
    import glob

    # 找最新的 player-career-wuyan 文件
    pattern = os.path.join(storage.data_dir, "player-career-wuyan.*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        print("[WARN] 未找到 player-career-wuyan 数据文件")
        return []

    try:
        with open(files[0], "r", encoding="utf-8") as f:
            career_data = json.load(f)

        hero_stats = career_data.get("data", {}).get("hero_stats", [])
        heroes = [h["hero_name"] for h in hero_stats if h.get("hero_name")]
        print(f"[INFO] 从 {os.path.basename(files[0])} 提取到 {len(heroes)} 个英雄: {', '.join(heroes)}")
        return heroes
    except Exception as e:
        print(f"[ERROR] 读取英雄列表失败: {e}")
        return []

def get_player_name_from_career(storage: KPLStorage) -> str:
    """从已保存的职业生涯数据中提取玩家名称"""
    import glob

    # 找最新的 player-career-wuyan 文件
    pattern = os.path.join(storage.data_dir, "player-career-wuyan.*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        print("[WARN] 未找到 player-career-wuyan 数据文件")
        return ""
    
    try:
        with open(files[0], "r", encoding="utf-8") as f:
            career_data = json.load(f)

        latest_nickname = career_data.get("data", {}).get("player_info", {}).get("latest_nickname", "")
        print(f"[INFO] 从 {os.path.basename(files[0])} 提取到选手名称: {latest_nickname}")
        return latest_nickname
    except Exception as e:
        print(f"[ERROR] 读取英雄列表失败: {e}")
        return ""

def get_latest_team_name_from_career(storage: KPLStorage) -> str:
    """从已保存的职业生涯数据中提取战队名称"""
    import glob

    # 找最新的 player-career-wuyan 文件
    pattern = os.path.join(storage.data_dir, "player-career-wuyan.*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        print("[WARN] 未找到 player-career-wuyan 数据文件"
              "请先运行一级抓取")
        return ""
    
    try: 
        with open(files[0], "r", encoding="utf-8") as f:
            career_data = json.load(f)

        latest_team = career_data.get("data", {}).get("player_info", {}).get("latest_team", "")
        print(f"[INFO] 从 {os.path.basename(files[0])} 提取到战队名称: {latest_team}")
        return latest_team
    except Exception as e:
        print(f"[ERROR] 读取战队名称失败: {e}")
        return ""

def fetch_hero_battles(crawler: KPLCrawler, storage: KPLStorage, season_id: str) -> dict:
    """
    二级抓取：遍历英雄列表，获取每个英雄的对局详情

    返回: { hero_name: { battles: [...], total, wins, loses }, ... }
    """
    heroes = get_hero_list_from_career(storage)
    if not heroes:
        return {}

    today_str = datetime.now().strftime(DATE_FORMAT)
    filename = f"player-hero-battles.{season_id}.{today_str}"
    filepath = os.path.join(storage.data_dir, f"{filename}.json")

    # 检查是否已存在
    if os.path.exists(filepath):
        print(f"[SKIP] player-hero-battles: 文件已存在 ({filename}.json)")
        return {}

    player_name = get_player_name_from_career(storage)

    result = {
        "season": season_id,
        "player_name": player_name,
        "fetch_time": datetime.now().isoformat(),
        "heroes": {},
    }

    success = 0
    fail = 0

    for hero_name in heroes:
        print(f"  [FETCH] {hero_name}...", end=" ")
        url = f"{API_PLAYER_HERO_BATTLES['url']}?player_name={player_name}&hero_name={hero_name}&season={season_id}"
        data = crawler.fetch(url)

        if data and data.get("code") == 200:
            hero_data = data.get("data", {})
            battles = hero_data.get("battle_details", [])
            wins = sum(1 for b in battles if b.get("is_win"))
            loses = len(battles) - wins

            result["heroes"][hero_name] = {
                "hero_id": battles[0].get("hero_id", "") if battles else "",
                "total": len(battles),
                "wins": wins,
                "loses": loses,
                "battles": battles,
            }
            print(f"✓ {len(battles)} 局")
            success += 1
        else:
            print(f"✗ 失败")
            fail += 1

    if result["heroes"]:
        storage.save(filename, result)
        print(f"[INFO] 英雄对局详情采集完成：成功 {success} 个英雄，失败 {fail} 个")
    else:
        print(f"[WARN] 未采集到任何英雄数据")

    return result


def run() -> int:
    """执行数据采集"""
    print("=" * 50)
    print("KPL 数据采集开始")
    print("=" * 50)

    crawler = KPLCrawler()
    storage = KPLStorage()

    # 获取最新赛季信息
    print("\n[INFO] 获取最新赛季信息...")
    season_info = get_latest_season(crawler)

    if season_info:
        # 从赛季详情中获取 tournament_id
        season_id = season_info.get("tournament_id")
        print(f"[INFO] 最新赛季：{season_id}")
        start_date = season_info.get("start_date", "未知")
        end_date = season_info.get("end_date", "未知")
        print(f"[INFO] 赛季时间段 ({start_date} ~ {end_date})")
        # 检查赛季是否活跃
        if not is_season_active(season_info):
            print(f"[SKIP] 赛季不在有效期内 ({start_date} ~ {end_date})，跳过采集")
            return 0
        
    else:
        season_id = CURRENT_SEASON
        print(f"[WARN] 无法获取赛季信息，使用默认值：{season_id}")

    success_count = 0
    fail_count = 0
    skip_count = 0

    today_str = datetime.now().strftime(DATE_FORMAT)

    target_team_name = get_latest_team_name_from_career(storage)
    if not target_team_name:
        target_team_name = TARGET_TEAM
    
    target_player_name = get_player_name_from_career(storage)
    if not target_player_name:
        target_player_name = TARGET_PLAYER
    
    print("\n" + "-" * 50)

    for api in APIS:
        if not api.get("enabled", True):
            print(f"[SKIP] {api['namespace']} (已禁用)")
            skip_count += 1
            continue

        namespace = api["namespace"]
        url = api["url"]

        # 替换 URL 中的参数
        url = url.replace("{season_id}", season_id)
        url = url.replace("{team_name}", target_team_name)

        # 确定文件名
        update_freq = api.get("update_freq", "daily")
        need_filter = api.get("need_filter", False)
        no_season = api.get("no_season", False)

        if no_season:
            # 不需要赛季 ID 的文件名
            if update_freq == "fixed":
                filename = f"{namespace}"
            else:
                filename = f"{namespace}.{today_str}"
        else:
            # 包含赛季 ID 的文件名
            if update_freq == "fixed":
                filename = f"{namespace}.{season_id}"
            else:
                filename = f"{namespace}.{season_id}.{today_str}"

        # 检查本地是否已有同名文件
        filepath = os.path.join(storage.data_dir, f"{filename}.json")
        if os.path.exists(filepath):
            print(f"[SKIP] {namespace}: 文件已存在 ({filename}.json)")
            skip_count += 1
            continue

        print(f"\n[FETCH] {namespace}: {url}")

        data = crawler.fetch(url)

        if data is not None:
            # 如果需要筛选选手数据
            if need_filter:
                filtered_data = filter_player_data(data, target_player_name)
                if filtered_data:
                    storage.save(filename, filtered_data)
                    success_count += 1
                else:
                    print(f"[WARN] {namespace} 未找到选手 {target_player_name} 的数据")
                    fail_count += 1
            else:
                storage.save(filename, data)
                success_count += 1
        else:
            print(f"[FAIL] {namespace} 采集失败")
            fail_count += 1

    # === 二级抓取：英雄对局详情 ===
    print("\n" + "-" * 50)
    print("[STEP 2] 英雄对局详情采集")
    print("-" * 50)
    fetch_hero_battles(crawler, storage, season_id)

    print("\n" + "=" * 50)
    print(f"采集完成：成功 {success_count} 个，失败 {fail_count} 个，跳过 {skip_count} 个")
    print(f"赛季：{season_id}")
    print(f"战队名：{target_team_name}")
    print(f"选手：{target_player_name}")
    print("=" * 50)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
