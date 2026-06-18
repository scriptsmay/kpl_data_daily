#!/usr/bin/env python3
"""Generate published data views for frontends and AI analysis."""

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from src.storage.config import DATA_DIR


SCHEMA_VERSION = 1
DATA_PATH = Path(DATA_DIR)
LATEST_PATH = DATA_PATH / "latest"
DERIVED_PATH = DATA_PATH / "derived"
DATE_RE = re.compile(r"^(?P<namespace>.+?)\.(?P<season>[A-Z]+[0-9A-Z]*)\.(?P<date>\d{8})\.json$")
NO_SEASON_DATE_RE = re.compile(r"^(?P<namespace>.+?)\.(?P<date>\d{8})\.json$")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_id() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S%z")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_data_file(path: Path) -> Dict[str, Optional[str]]:
    name = path.name
    m = DATE_RE.match(name)
    if m:
        return m.groupdict()

    m = NO_SEASON_DATE_RE.match(name)
    if m:
        info = m.groupdict()
        info["season"] = None
        return info

    if name.endswith(".json"):
        stem = name[:-5]
        parts = stem.split(".")
        if len(parts) == 2 and re.match(r"^[A-Z]+[0-9A-Z]*$", parts[1]):
            return {"namespace": parts[0], "season": parts[1], "date": None}
        return {"namespace": stem, "season": None, "date": None}

    return {"namespace": path.stem, "season": None, "date": None}


def iter_raw_json_files() -> Iterable[Path]:
    excluded_dirs = {"latest", "derived", "archive", "_reports"}
    for path in sorted(DATA_PATH.glob("*.json")):
        if path.parent.name not in excluded_dirs:
            yield path


def generate_manifest(generated_at: str, current_build_id: str) -> Dict[str, Any]:
    files = []
    for path in iter_raw_json_files():
        info = parse_data_file(path)
        stat = path.stat()
        files.append(
            {
                "namespace": info["namespace"],
                "season": info["season"],
                "date": info["date"],
                "file": path.relative_to(DATA_PATH).as_posix(),
                "hash": sha256_file(path),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).astimezone().isoformat(timespec="seconds"),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "build_id": current_build_id,
        "file_count": len(files),
        "files": files,
    }
    write_json(DATA_PATH / "manifest.json", manifest)
    return manifest


def latest_file(namespace: str, season: Optional[str] = None) -> Optional[Path]:
    candidates = []
    for path in iter_raw_json_files():
        info = parse_data_file(path)
        if info["namespace"] == namespace and info["season"] == season:
            candidates.append((info["date"] or "00000000", path))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def get_current_season() -> Dict[str, str]:
    seasons_path = latest_file("seasons-list")
    if not seasons_path:
        return {"current": "", "season_name": ""}

    seasons = load_json(seasons_path)
    if isinstance(seasons, dict):
        seasons = seasons.get("data", [])

    for season in seasons:
        if season.get("is_latest") == 1:
            return {
                "current": season.get("tournament_id", ""),
                "season_name": season.get("tournament_name", ""),
            }
    return {"current": "", "season_name": ""}


def generate_latest(current_season: str, current_info: Dict[str, str], generated_at: str, current_build_id: str) -> None:
    if LATEST_PATH.exists():
        shutil.rmtree(LATEST_PATH)
    LATEST_PATH.mkdir(parents=True, exist_ok=True)

    current_payload = {
        "schema_version": SCHEMA_VERSION,
        "current": current_info.get("current", ""),
        "season_name": current_info.get("season_name", ""),
        "updated_at": generated_at,
        "build_id": current_build_id,
    }
    write_json(LATEST_PATH / "current-season.json", current_payload)

    seasons_path = latest_file("seasons-list")
    if seasons_path:
        shutil.copyfile(seasons_path, LATEST_PATH / "seasons-list.json")

    namespaces = {
        info["namespace"]
        for info in (parse_data_file(p) for p in iter_raw_json_files())
        if info["season"] == current_season and info["date"]
    }

    for namespace in sorted(namespaces):
        src = latest_file(namespace, current_season)
        if src:
            dst = LATEST_PATH / current_season / f"{namespace}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    career = latest_file("player-career-wuyan")
    if career:
        dst = LATEST_PATH / "player-career-wuyan.json"
        shutil.copyfile(career, dst)


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def load_latest_payload(namespace: str, season: Optional[str] = None) -> Optional[Any]:
    if season:
        path = LATEST_PATH / season / f"{namespace}.json"
    else:
        path = LATEST_PATH / f"{namespace}.json"
    if not path.exists():
        return None
    return load_json(path)


def derived_payload(season: str, generated_at: str, current_build_id: str, data: Any) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": generated_at,
        "build_id": current_build_id,
        "data": data,
    }


def first_item(payload: Any) -> Dict[str, Any]:
    data = unwrap_data(payload)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


def generate_derived(current_season: str, generated_at: str, current_build_id: str) -> None:
    season_dir = DERIVED_PATH / current_season
    season_dir.mkdir(parents=True, exist_ok=True)

    career = load_latest_payload("player-career-wuyan")
    career_data = unwrap_data(career) if career else {}
    overview = {
        "player_info": career_data.get("player_info", {}),
        "career_summary": career_data.get("career_summary", {}),
        "season_stats": career_data.get("season_stats", []),
        "team_stats": career_data.get("team_stats", []),
        "hero_stats": career_data.get("hero_stats", []),
        "recent_matches": career_data.get("match_details", [])[:10],
    }
    write_json(season_dir / "overview.json", derived_payload(current_season, generated_at, current_build_id, overview))

    abilities = load_latest_payload("player-abilities", current_season) or {}
    write_json(season_dir / "abilities.json", derived_payload(current_season, generated_at, current_build_id, abilities))

    ranking = load_latest_payload("all-player-stats", current_season) or {}
    write_json(season_dir / "ranking.json", derived_payload(current_season, generated_at, current_build_id, ranking))

    hero_summary = load_latest_payload("player-hero-summary", current_season) or {}
    hero_battles = load_latest_payload("player-hero-battles", current_season) or {}
    hero_win_rate = load_latest_payload("hero-win-rate", current_season) or {}
    heroes = {
        "summary": unwrap_data(hero_summary) if hero_summary else [],
        "battles": hero_battles.get("heroes", {}) if isinstance(hero_battles, dict) else {},
        "league_win_rate": unwrap_data(hero_win_rate) if hero_win_rate else [],
    }
    write_json(season_dir / "heroes.json", derived_payload(current_season, generated_at, current_build_id, heroes))

    win = load_latest_payload("player-win-stats", current_season) or {}
    lose = load_latest_payload("player-lose-stats", current_season) or {}
    win_lose = {
        "win": first_item(win),
        "lose": first_item(lose),
        "win_source": win,
        "lose_source": lose,
    }
    write_json(season_dir / "win-lose.json", derived_payload(current_season, generated_at, current_build_id, win_lose))

    insights = generate_rule_insights(current_season, overview, heroes, win_lose)
    write_json(season_dir / "insights.json", derived_payload(current_season, generated_at, current_build_id, insights))


def parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("%", ""))
    except ValueError:
        return None


def generate_rule_insights(season: str, overview: Dict[str, Any], heroes: Dict[str, Any], win_lose: Dict[str, Any]) -> Dict[str, Any]:
    highlights = []
    summary = overview.get("career_summary", {})
    if summary.get("total_battles"):
        highlights.append(f"无言生涯已累计 {summary.get('total_battles')} 小局，胜率 {summary.get('win_rate', '-')}")

    hero_list = heroes.get("summary") or []
    if hero_list:
        top = sorted(hero_list, key=lambda h: h.get("total_matches") or 0, reverse=True)[0]
        highlights.append(f"{season} 当前使用最多英雄是 {top.get('hero_name')}，出场 {top.get('total_matches')} 次，胜率 {top.get('win_rate')}")

    win = win_lose.get("win") or {}
    lose = win_lose.get("lose") or {}
    if win and lose:
        win_kda = win.get("avg_kda")
        lose_kda = lose.get("avg_kda")
        if win_kda is not None and lose_kda is not None:
            highlights.append(f"获胜时平均 KDA 为 {win_kda}，失败时为 {lose_kda}")

    if not highlights:
        highlights.append("数据持续积累中，更多趋势洞察将在样本增加后生成")

    return {
        "headline": highlights[0],
        "highlights": highlights,
        "risk_notes": ["自动规则生成，仅供前端展示和人工复核，不作为最终赛训结论"],
    }


def run() -> None:
    generated_at = now_iso()
    current_build_id = build_id()
    current_info = get_current_season()
    current_season = current_info.get("current", "")
    if not current_season:
        raise RuntimeError("无法从 seasons-list 获取当前赛季")

    generate_manifest(generated_at, current_build_id)
    generate_latest(current_season, current_info, generated_at, current_build_id)
    generate_derived(current_season, generated_at, current_build_id)
    print(f"[INFO] post_process 完成：season={current_season}, build_id={current_build_id}")


if __name__ == "__main__":
    run()
