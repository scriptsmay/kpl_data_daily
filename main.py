#!/usr/bin/env python3
"""
KPL 数据采集工具

每日定时抓取配置中的 API 接口数据
- 固定 API: 保存为 {命名空间}{赛季 ID}.json
- 每日更新 API: 保存为 {命名空间}{赛季 ID}.{日期}.json
"""

import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.crawler.config import (
    APIS,
    CURRENT_SEASON,
    DATA_DIR,
    DATE_FORMAT,
    HEADERS,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    TARGET_PLAYER,
    TARGET_TEAM,
)
from src.crawler.fetcher import KPLCrawler
from src.storage.saver import KPLStorage


def get_latest_season(crawler: KPLCrawler) -> Optional[Dict]:
    """获取最新赛季信息"""
    url = "http://47.102.210.150:5006/seasons/list"
    data = crawler.fetch(url)

    if not data:
        return None

    # 找到 project=KPL 且 is_latest=1 的赛季
    for season in data:
        if season.get("project") == "KPL" and season.get("is_latest") == 1:
            season_id = season.get("tournament_name")
            # 获取详细赛季信息（包含开始/结束日期）
            season_detail_url = f"http://47.102.210.150:5006/season/{season_id}"
            season_detail = crawler.fetch(season_detail_url)
            return season_detail

    return None


def is_season_active(season: Dict) -> bool:
    """检查赛季是否在有效期内（包括结束日期的第二天）"""
    if not season:
        return False

    start_date_str = season.get("start_date")
    end_date_str = season.get("end_date")

    if not start_date_str or not end_date_str:
        return True  # 没有日期信息，默认执行

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    today = datetime.now()

    # 结束日期的第二天
    end_date_plus_one = end_date + timedelta(days=1)

    return start_date <= today <= end_date_plus_one


def filter_player_data(data: Any, player_name: str) -> Any:
    """从批量数据中筛选指定选手的数据"""
    # 处理 {code, data: [...]} 格式
    if isinstance(data, dict) and "data" in data:
        inner_data = data["data"]
        if isinstance(inner_data, list):
            for item in inner_data:
                if isinstance(item, dict):
                    name_fields = ["playerName", "player_name", "name", "player", "displayName"]
                    for field in name_fields:
                        if player_name in str(item.get(field, "")):
                            # 返回完整响应，但 data 字段只包含筛选后的选手
                            result = data.copy()
                            result["data"] = item
                            return result
            # 如果没有找到，返回原始数据
            return data
    
    # 处理直接是列表的格式
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name_fields = ["playerName", "player_name", "name", "player", "displayName"]
                for field in name_fields:
                    if player_name in str(item.get(field, "")):
                        return item
        return data
    
    return data


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
        season_id = season_info.get("tournament_name", CURRENT_SEASON)
        print(f"[INFO] 最新赛季：{season_id}")

        # 检查赛季是否活跃
        if not is_season_active(season_info):
            start_date = season_info.get("start_date", "未知")
            end_date = season_info.get("end_date", "未知")
            print(f"[SKIP] 赛季不在有效期内 ({start_date} ~ {end_date})，跳过采集")
            return 0
    else:
        season_id = CURRENT_SEASON
        print(f"[WARN] 无法获取赛季信息，使用默认值：{season_id}")

    success_count = 0
    fail_count = 0
    skip_count = 0

    today_str = datetime.now().strftime(DATE_FORMAT)

    for api in APIS:
        if not api.get("enabled", True):
            print(f"[SKIP] {api['namespace']} (已禁用)")
            skip_count += 1
            continue

        namespace = api["namespace"]
        url = api["url"]

        # 替换 URL 中的参数
        url = url.replace("{season_id}", season_id)
        url = url.replace("{team_name}", TARGET_TEAM)

        # 确定文件名
        update_freq = api.get("update_freq", "daily")
        need_filter = api.get("need_filter", False)

        if update_freq == "fixed":
            filename = f"{namespace}.{season_id}"
        else:
            filename = f"{namespace}.{season_id}.{today_str}"

        print(f"\n[FETCH] {namespace}: {url}")

        data = crawler.fetch(url)

        if data is not None:
            # 如果需要筛选选手数据
            if need_filter:
                filtered_data = filter_player_data(data, TARGET_PLAYER)
                if filtered_data:
                    storage.save(filename, filtered_data)
                    success_count += 1
                else:
                    print(f"[WARN] {namespace} 未找到选手 {TARGET_PLAYER} 的数据")
                    fail_count += 1
            else:
                storage.save(filename, data)
                success_count += 1
        else:
            print(f"[FAIL] {namespace} 采集失败")
            fail_count += 1

    print("\n" + "=" * 50)
    print(f"采集完成：成功 {success_count} 个，失败 {fail_count} 个，跳过 {skip_count} 个")
    print(f"赛季：{season_id}")
    print(f"关注选手：{TARGET_PLAYER}")
    print("=" * 50)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
