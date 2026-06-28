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
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
load_dotenv()

from src.crawler.config import (
    APIS,
    CURRENT_SEASON,
    API_PLAYER_HERO,
    API_PLAYER_HERO_BATTLES,
    DATE_FORMAT,
    TARGET_PLAYER,
    TARGET_TEAM,
    REQUEST_DELAY_LARGE,
)
from src.crawler.fetcher import KPLCrawler
from src.storage.saver import KPLStorage
from post_process import run as run_post_process


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


def _player_match_terms(player_name: str) -> List[str]:
    """Return stable player-name terms for cross-season matching."""
    terms = {TARGET_PLAYER}
    if player_name:
        terms.add(player_name)
        if "." in player_name:
            terms.add(player_name.split(".")[-1])
    return [term for term in terms if term]


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
            # 检查是否有任何字段匹配。历史赛季可能只有昵称“无言”，
            # 当前赛季可能是“KSG.无言”，因此用稳定关键词集合匹配。
            match_terms = _player_match_terms(player_name)
            if any(
                term in str(item.get(field, ""))
                for field in name_fields
                for term in match_terms
            ):
                filtered_results.append(item)

    # 3. 根据原始格式返回结果
    if is_wrapped_dict:
        result = data.copy()
        result["data"] = filtered_results
        return result
    
    return filtered_results


def get_hero_list_from_summary(storage: KPLStorage, season_id: str = None) -> list:
    """从已保存的 player-hero-summary 数据中提取英雄列表

    Args:
        storage: 存储器实例
        season_id: 赛季 ID；指定时从 data/seasons/{season}/latest/ 读取，
                   否则从全局 data/ 目录读取（兼容旧逻辑）
    """
    import glob

    if season_id:
        # 历史赛季：从 data/seasons/{season}/latest/{season}/player-hero-summary.json 读取
        season_summary = Path(storage.data_dir) / "seasons" / season_id / "latest" / season_id / "player-hero-summary.json"
        if season_summary.exists():
            files = [str(season_summary)]
        else:
            # 回退：从全局 data/ 读取（可能有历史快照）
            pattern = os.path.join(storage.data_dir, f"player-hero-summary.{season_id}.*.json")
            files = sorted(glob.glob(pattern), reverse=True)
    else:
        # 当前赛季：从全局 data/ 读取最新
        pattern = os.path.join(storage.data_dir, "player-hero-summary.*.json")
        files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        print(f"[WARN] 未找到 player-hero-summary 数据文件（赛季：{season_id or '全局'}）")
        return []

    try:
        with open(files[0], "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        # 从 data 数组中提取 hero_name
        data_list = summary_data.get("data", [])
        if isinstance(data_list, list):
            heroes = [item["hero_name"] for item in data_list if item.get("hero_name")]
        else:
            heroes = []

        print(f"[INFO] 从 {os.path.basename(files[0])} 提取到 {len(heroes)} 个英雄：{', '.join(heroes)}")
        return heroes
    except Exception as e:
        print(f"[ERROR] 读取英雄列表失败：{e}")
        return []


def resolve_target_identity(storage: KPLStorage, season_id: str) -> dict:
    """从指定赛季的已有数据中解析目标选手的完整名称和战队名称。

    搜索优先级：
    1. data/seasons/{season}/latest/{season}/ 下的 player-hero-summary / all-player-stats / player-abilities
    2. data/ 下该赛季的 raw 文件

    返回: {"player_name": str, "team_name": str}
    找不到时回退到 config 中的 TARGET_PLAYER / TARGET_TEAM。
    """
    from pathlib import Path

    player_name = ""
    team_name = ""

    # 候选来源：按优先级搜索
    search_files = []
    season_latest_dir = Path(storage.data_dir) / "seasons" / season_id / "latest" / season_id
    if season_latest_dir.exists():
        for ns in ["player-hero-summary", "all-player-stats", "player-abilities"]:
            p = season_latest_dir / f"{ns}.json"
            if p.exists():
                search_files.append(p)

    # 回退：从全局 data/ 目录搜索该赛季文件
    if not search_files:
        import glob
        for ns in ["player-hero-summary", "all-player-stats", "player-abilities"]:
            pattern = os.path.join(storage.data_dir, f"{ns}.{season_id}.*.json")
            files = sorted(glob.glob(pattern), reverse=True)
            if files:
                search_files.append(Path(files[0]))

    # 从 data/seasons/{season}/latest/player-career-wuyan.json 也可提取
    career_path = Path(storage.data_dir) / "seasons" / season_id / "latest" / "player-career-wuyan.json"
    if career_path.exists():
        search_files.append(career_path)
    # 全局 career 文件
    global_career = Path(storage.data_dir) / "latest" / "player-career-wuyan.json"
    if global_career.exists():
        search_files.append(global_career)

    for fpath in search_files:
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            inner = data.get("data", data)
            items = inner if isinstance(inner, list) else []

            # 搜索选手名（包含"无言"的完整名称），并优先从同一条记录取战队。
            if not player_name:
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("player_name", item.get("playerName", item.get("name", "")))
                        if "无言" in str(name):
                            player_name = str(name)
                            tn = item.get("team_name", item.get("teamName", item.get("team", "")))
                            if tn:
                                team_name = str(tn)
                            break

            # 从 career 数据提取
            if not player_name and isinstance(inner, dict):
                pi = inner.get("player_info", {})
                nn = pi.get("latest_nickname", "")
                if "无言" in nn:
                    player_name = nn
                if not team_name:
                    team_name = pi.get("latest_team", "")

            # 搜索战队名：优先从目标选手记录中取，避免全量数据第一条误判。
            if not team_name:
                match_terms = _player_match_terms(player_name)
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("player_name", item.get("playerName", item.get("name", "")))
                        tn = item.get("team_name", item.get("teamName", item.get("team", "")))
                        if tn and any(term in str(name) for term in match_terms):
                            team_name = str(tn)
                            break

            if player_name and team_name:
                break
        except Exception:
            continue

    result = {
        "player_name": player_name or TARGET_PLAYER,
        "team_name": team_name or TARGET_TEAM,
    }
    print(f"[INFO] 赛季 {season_id} 身份解析：选手={result['player_name']}，战队={result['team_name']}")
    return result



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
    heroes = get_hero_list_from_summary(storage)
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
        
        try:
            # 大数据量接口，增加超时时间到 60秒，间隔增加到 3秒
            data = crawler.fetch(url, timeout=60, delay=REQUEST_DELAY_LARGE)

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
        except Exception as e:
            print(f"✗ 异常: {e}")
            fail += 1

    if result["heroes"]:
        storage.save(filename, result)
        print(f"[INFO] 英雄对局详情采集完成：成功 {success} 个英雄，失败 {fail} 个")
    else:
        print(f"[WARN] 未采集到任何英雄数据")

    return result


def _api_unavailable_path(data_dir: str) -> str:
    """返回 api_unavailable 记录文件路径。"""
    return os.path.join(data_dir, "_api_unavailable.json")


def _load_api_unavailable(data_dir: str) -> dict:
    """加载已知不可用 API 记录。格式: {"{season}:{namespace}": {"reason": str, "recorded_at": str}}"""
    path = _api_unavailable_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_api_unavailable(data_dir: str, records: dict) -> None:
    """保存不可用 API 记录。"""
    path = _api_unavailable_path(data_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        f.write("\n")


def record_api_unavailable(season_id: str, namespace: str, reason: str, data_dir: str = None) -> None:
    """记录一个 API 为不可用，避免反复重试。"""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
    records = _load_api_unavailable(data_dir)
    key = f"{season_id}:{namespace}"
    records[key] = {
        "reason": reason,
        "recorded_at": datetime.now().isoformat(),
    }
    _save_api_unavailable(data_dir, records)
    print(f"[INFO] 已记录 API 不可用: {key} ({reason})")


def _is_valid_raw(namespace: str, season_id: str, data_dir: str) -> dict:
    """检查指定 season/namespace 的 raw 数据质量。

    返回: {"status": str, "file": str|None, "detail": str}
    status: missing / valid / empty_data / invalid_json / api_unavailable
    """
    import glob
    from pathlib import Path

    # 先检查是否已记录为不可用
    unavailable = _load_api_unavailable(data_dir)
    key = f"{season_id}:{namespace}"
    if key in unavailable:
        return {"status": "api_unavailable", "file": None, "detail": unavailable[key].get("reason", "已记录为不可用")}

    # 搜索文件：支持两种格式
    # 1. {namespace}.{season_id}.{date}.json（每日更新）
    # 2. {namespace}.{season_id}.json（固定数据）
    pattern = os.path.join(data_dir, f"{namespace}.{season_id}.*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    # 回退：检查固定格式（无日期后缀）
    if not files:
        fixed_path = os.path.join(data_dir, f"{namespace}.{season_id}.json")
        if os.path.exists(fixed_path):
            files = [fixed_path]

    if not files:
        return {"status": "missing", "file": None, "detail": "无文件"}

    fpath = files[0]
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"status": "invalid_json", "file": fpath, "detail": "JSON 解析失败"}
    except Exception as e:
        return {"status": "invalid_json", "file": fpath, "detail": str(e)}

    # 检查 data 是否为空
    inner = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(inner, list) and len(inner) == 0:
        return {"status": "empty_data", "file": fpath, "detail": "data 为空数组"}

    return {"status": "valid", "file": fpath, "detail": f"数据有效（{os.path.getsize(fpath)} bytes）"}


def audit_raw_season(season_id: str, data_dir: str = None) -> dict:
    """对指定赛季执行 raw audit，返回每个 namespace 的状态。

    Returns: {"season": str, "namespaces": {namespace: {"status": str, ...}}, "summary": {...}}
    """
    from src.crawler.config import APIS

    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")

    namespaces = {}
    # 从 APIS 配置中提取需要审计的 namespace（排除 no_season 和无需季节的）
    for api in APIS:
        ns = api["namespace"]
        no_season = api.get("no_season", False)
        if no_season:
            continue  # 不属于特定赛季
        namespaces[ns] = _is_valid_raw(ns, season_id, data_dir)

    # 统计
    summary = {
        "total": len(namespaces),
        "valid": sum(1 for v in namespaces.values() if v["status"] == "valid"),
        "empty_data": sum(1 for v in namespaces.values() if v["status"] == "empty_data"),
        "missing": sum(1 for v in namespaces.values() if v["status"] == "missing"),
        "invalid_json": sum(1 for v in namespaces.values() if v["status"] == "invalid_json"),
        "api_unavailable": sum(1 for v in namespaces.values() if v["status"] == "api_unavailable"),
    }

    return {"season": season_id, "namespaces": namespaces, "summary": summary}


def print_audit_report(audit: dict) -> None:
    """打印 raw audit 报告。"""
    season = audit["season"]
    summary = audit["summary"]

    print(f"\n{'=' * 60}")
    print(f"🔍 Raw Audit: {season}")
    print(f"{'=' * 60}")
    print(f"  总计: {summary['total']} 个 namespace")
    print(f"  ✅ valid: {summary['valid']}")
    print(f"  ⚠️  empty_data: {summary['empty_data']}")
    print(f"  ❌ missing: {summary['missing']}")
    print(f"  💥 invalid_json: {summary['invalid_json']}")
    print(f"  🚫 api_unavailable: {summary.get('api_unavailable', 0)}")

    # 列出需要修复的（排除 api_unavailable，这些是已知不可用的）
    issues = {ns: info for ns, info in audit["namespaces"].items() if info["status"] not in ("valid", "api_unavailable")}
    if issues:
        print(f"\n  需要修复的 namespace:")
        for ns, info in sorted(issues.items()):
            print(f"    {info['status']:15s} {ns}: {info['detail']}")

    # 列出已确认不可用的
    unavail = {ns: info for ns, info in audit["namespaces"].items() if info["status"] == "api_unavailable"}
    if unavail:
        print(f"\n  已确认不可用（不会重试）:")
        for ns, info in sorted(unavail.items()):
            print(f"    🚫 {ns}: {info['detail']}")
    print(f"{'=' * 60}\n")


def import_archive_kcc2025(data_dir: str = None) -> dict:
    """将 doc/archive/ 中的 KCC2025 快照迁移到 data/ 目录。

    返回: {"imported": [...], "skipped": [...], "errors": [...]}
    """
    from pathlib import Path
    from datetime import datetime

    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")

    archive_dir = os.path.join(os.path.dirname(__file__), "doc", "archive")
    if not os.path.exists(archive_dir):
        return {"imported": [], "skipped": [], "errors": [{"file": archive_dir, "error": "archive 目录不存在"}]}

    # namespace 映射：旧命名 → 新命名
    ns_mapping = {
        "player_stats": "player-stats",
        "records": "season-records",
    }

    imported = []
    skipped = []
    errors = []

    for fname in os.listdir(archive_dir):
        if not fname.endswith(".KCC2025.json"):
            continue

        src_path = os.path.join(archive_dir, fname)
        # 解析 namespace
        stem = fname.replace(".KCC2025.json", "")
        ns = ns_mapping.get(stem, stem)

        # 目标文件名：{namespace}.KCC2025.{date}.json
        today_str = datetime.now().strftime("%Y%m%d")
        dst_name = f"{ns}.KCC2025.{today_str}.json"
        dst_path = os.path.join(data_dir, dst_name)

        if os.path.exists(dst_path):
            skipped.append({"file": fname, "reason": f"目标已存在: {dst_name}"})
            continue

        try:
            import shutil
            os.makedirs(data_dir, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            imported.append({"src": fname, "dst": dst_name})
            print(f"  [IMPORT] {fname} → {dst_name}")
        except Exception as e:
            errors.append({"file": fname, "error": str(e)})

    return {"imported": imported, "skipped": skipped, "errors": errors}


def fetch_season_data(
    season_id: str,
    force: bool = False,
    target_identity: dict = None,
) -> dict:
    """对指定赛季执行原始数据抓取。

    Args:
        season_id: 目标赛季 ID（如 KCC2025、KPL2026S1）
        force: True 时强制重抓已有文件
        target_identity: {"player_name": str, "team_name"}；None 时自动解析

    Returns: {"success": int, "fail": int, "skip": int, "details": [...]}
    """
    print(f"\n{'=' * 50}")
    print(f"📥 抓取赛季原始数据: {season_id}")
    print(f"{'=' * 50}")

    crawler = KPLCrawler()
    storage = KPLStorage()

    # 身份解析
    if target_identity is None:
        target_identity = resolve_target_identity(storage, season_id)

    player_name = target_identity["player_name"]
    team_name = target_identity["team_name"]

    success_count = 0
    fail_count = 0
    skip_count = 0
    details = []

    today_str = datetime.now().strftime(DATE_FORMAT)

    for api in APIS:
        if not api.get("enabled", True):
            continue

        namespace = api["namespace"]
        no_season = api.get("no_season", False)
        if no_season:
            continue  # 跳过不属于特定赛季的 API（如 seasons-list）

        url = api["url"]
        url = url.replace("{season_id}", season_id)
        url = url.replace("{team_name}", team_name)

        update_freq = api.get("update_freq", "daily")
        need_filter = api.get("need_filter", False)

        if update_freq == "fixed":
            filename = f"{namespace}.{season_id}"
        else:
            filename = f"{namespace}.{season_id}.{today_str}"

        filepath = os.path.join(storage.data_dir, f"{filename}.json")

        # 增量策略：检查已有文件和不可用记录
        quality = _is_valid_raw(namespace, season_id, storage.data_dir)
        if quality["status"] == "api_unavailable":
            print(f"[SKIP] {namespace}: 已记录为不可用（{quality['detail']}）")
            skip_count += 1
            details.append({"namespace": namespace, "result": "api_unavailable"})
            continue

        if os.path.exists(filepath) and not force:
            if quality["status"] == "valid":
                print(f"[SKIP] {namespace}: 有效文件已存在")
                skip_count += 1
                details.append({"namespace": namespace, "result": "skipped_valid"})
                continue
            elif quality["status"] == "empty_data":
                print(f"[RE-FETCH] {namespace}: 已有文件为空数据，重新抓取")
            else:
                print(f"[RE-FETCH] {namespace}: {quality['detail']}")

        print(f"\n[FETCH] {namespace}: {url}")

        try:
            data = crawler.fetch(url)

            if data is not None:
                if need_filter:
                    filtered_data = filter_player_data(data, player_name)
                    if filtered_data:
                        storage.save(filename, filtered_data)
                        success_count += 1
                        details.append({"namespace": namespace, "result": "fetched"})
                    else:
                        print(f"[WARN] {namespace} 未找到选手 {player_name} 的数据")
                        # 保存空结果标记
                        empty = {"data": [], "season": season_id, "player_name": player_name, "fetch_time": datetime.now().isoformat(), "note": "api_empty_or_player_not_found"}
                        storage.save(filename, empty)
                        fail_count += 1
                        details.append({"namespace": namespace, "result": "api_empty"})
                else:
                    storage.save(filename, data)
                    success_count += 1
                    details.append({"namespace": namespace, "result": "fetched"})
            else:
                print(f"[FAIL] {namespace} 采集失败")
                fail_count += 1
                details.append({"namespace": namespace, "result": "failed"})
        except Exception as e:
            err_str = str(e)
            # 检测 404 错误，记录为 api_unavailable
            if "404" in err_str or "NOT FOUND" in err_str:
                print(f"[WARN] {namespace} API 404，记录为不可用")
                record_api_unavailable(season_id, namespace, f"HTTP 404: {err_str[:200]}", storage.data_dir)
                details.append({"namespace": namespace, "result": "api_unavailable"})
            else:
                print(f"[ERROR] {namespace} 采集异常: {e}")
                fail_count += 1
                details.append({"namespace": namespace, "result": "error", "error": str(e)})

    # === 二级抓取：英雄对局详情 ===
    print(f"\n--- 英雄对局详情: {season_id} ---")

    hero_summary_ns = "player-hero-summary"
    quality = _is_valid_raw(hero_summary_ns, season_id, storage.data_dir)
    if quality["status"] == "valid":
        try:
            result = fetch_hero_battles_for_season(crawler, storage, season_id, player_name)
            if result and result.get("heroes"):
                success_count += 1
                details.append({"namespace": "player-hero-battles", "result": "fetched"})
            else:
                details.append({"namespace": "player-hero-battles", "result": "api_empty"})
        except Exception as e:
            print(f"[ERROR] 英雄对局详情采集异常: {e}")
            fail_count += 1
            details.append({"namespace": "player-hero-battles", "result": "error", "error": str(e)})
    else:
        print(f"[SKIP] player-hero-battles: 需要有效的 player-hero-summary（当前状态: {quality['status']}）")
        details.append({"namespace": "player-hero-battles", "result": "skipped_no_summary"})

    print(f"\n{'=' * 50}")
    print(f"📥 赛季 {season_id} 抓取完成：成功 {success_count}，失败 {fail_count}，跳过 {skip_count}")
    print(f"{'=' * 50}")

    return {"success": success_count, "fail": fail_count, "skip": skip_count, "details": details}


def fetch_hero_battles_for_season(
    crawler: KPLCrawler,
    storage: KPLStorage,
    season_id: str,
    player_name: str,
) -> dict:
    """为指定赛季抓取英雄对局详情（使用 season-specific player_name）。

    返回: {"season": str, "player_name": str, "heroes": {...}}
    """
    heroes = get_hero_list_from_summary(storage, season_id=season_id)
    if not heroes:
        return {}

    today_str = datetime.now().strftime(DATE_FORMAT)
    filename = f"player-hero-battles.{season_id}.{today_str}"
    filepath = os.path.join(storage.data_dir, f"{filename}.json")

    if os.path.exists(filepath):
        print(f"[SKIP] player-hero-battles: 文件已存在 ({filename}.json)")
        return {}

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

        try:
            data = crawler.fetch(url, timeout=60, delay=REQUEST_DELAY_LARGE)

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
        except Exception as e:
            print(f"✗ 异常: {e}")
            fail += 1

    if result["heroes"]:
        storage.save(filename, result)
        print(f"[INFO] 英雄对局详情采集完成：成功 {success} 个英雄，失败 {fail} 个")
    else:
        print(f"[WARN] 未采集到任何英雄数据")

    return result


def run(season_id: str = None, force: bool = False) -> int:
    """执行数据采集。

    Args:
        season_id: 指定赛季 ID 时执行历史赛季抓取；None 时抓取最新赛季（原行为）
        force: True 时强制重抓已有文件
    """
    if season_id:
        # 历史赛季模式
        result = fetch_season_data(season_id, force=force)
        # 后处理
        try:
            print(f"\n[STEP 3] 生成 {season_id} derived / manifest")
            run_post_process(season_override=season_id)
        except Exception as e:
            print(f"[ERROR] 数据后处理失败: {e}")
        return 0 if result["success"] > 0 or result["skip"] > 0 else 1

    # === 原有逻辑：抓取最新赛季 ===
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
        season_id_val = season_info.get("tournament_id")
        print(f"[INFO] 最新赛季：{season_id_val}")
        start_date = season_info.get("start_date", "未知")
        end_date = season_info.get("end_date", "未知")
        print(f"[INFO] 赛季时间段 ({start_date} ~ {end_date})")
        # 检查赛季是否活跃
        if not is_season_active(season_info):
            print(f"[SKIP] 赛季不在有效期内 ({start_date} ~ {end_date})，跳过采集")
            return 0

    else:
        season_id_val = CURRENT_SEASON
        print(f"[WARN] 无法获取赛季信息，使用默认值：{season_id_val}")

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
        url = url.replace("{season_id}", season_id_val)
        url = url.replace("{team_name}", target_team_name)

        # 确定文件名
        update_freq = api.get("update_freq", "daily")
        need_filter = api.get("need_filter", False)
        no_season = api.get("no_season", False)
        overwrite = api.get("overwrite", False)

        if no_season:
            # 不需要赛季 ID 的文件名
            if update_freq == "fixed":
                filename = f"{namespace}"
            else:
                filename = f"{namespace}.{today_str}"
        else:
            # 包含赛季 ID 的文件名
            if update_freq == "fixed":
                filename = f"{namespace}.{season_id_val}"
            else:
                filename = f"{namespace}.{season_id_val}.{today_str}"

        # 检查本地是否已有同名文件
        filepath = os.path.join(storage.data_dir, f"{filename}.json")
        if os.path.exists(filepath) and not overwrite:
            print(f"[SKIP] {namespace}: 文件已存在 ({filename}.json)")
            skip_count += 1
            continue

        print(f"\n[FETCH] {namespace}: {url}")

        try:
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
        except Exception as e:
            print(f"[ERROR] {namespace} 采集异常: {e}")
            fail_count += 1

    # === 二级抓取：英雄对局详情 ===
    print("\n" + "-" * 50)
    print("[STEP 2] 英雄对局详情采集")
    print("-" * 50)

    try:
        fetch_hero_battles(crawler, storage, season_id_val)
    except Exception as e:
        print(f"[ERROR] 英雄对局详情采集异常: {e}")

    print("\n" + "=" * 50)
    print(f"采集完成：成功 {success_count} 个，失败 {fail_count} 个，跳过 {skip_count} 个")
    print(f"赛季：{season_id_val}")
    print(f"战队名：{target_team_name}")
    print(f"选手：{target_player_name}")
    print("=" * 50)

    try:
        print("\n[STEP 3] 生成 latest / manifest / derived")
        run_post_process()
    except Exception as e:
        print(f"[ERROR] 数据后处理失败: {e}")

    # 只要有成功的数据就返回 0，让后续步骤继续
    return 0 if success_count > 0 or skip_count > 0 else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KPL 数据采集工具")
    parser.add_argument("--season", help="指定赛季 ID 进行历史赛季采集（如 KCC2025）")
    parser.add_argument("--force", action="store_true", help="强制重抓已有文件")
    parser.add_argument("--audit", metavar="SEASON", help="对指定赛季执行 raw audit（如 KCC2025）")
    parser.add_argument("--import-archive", action="store_true", help="导入 doc/archive/ 中的 KCC2025 快照")
    args = parser.parse_args()

    if args.audit:
        audit_result = audit_raw_season(args.audit)
        print_audit_report(audit_result)
        sys.exit(0)
    elif args.import_archive:
        result = import_archive_kcc2025()
        print(f"\n导入结果：导入 {len(result['imported'])} 个，跳过 {len(result['skipped'])} 个，错误 {len(result['errors'])} 个")
        if result["errors"]:
            for err in result["errors"]:
                print(f"  [ERROR] {err['file']}: {err['error']}")
        sys.exit(0)
    else:
        sys.exit(run(season_id=args.season, force=args.force))
