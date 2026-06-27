#!/usr/bin/env python3
"""Generate published data views for frontends and AI analysis."""

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv
load_dotenv()

from src.storage.config import DATA_DIR
from src.analysis.metrics import compute_all as compute_metrics
from src.analysis.trends import compute_trends
from src.analysis.growth_path import generate as generate_growth_path


SCHEMA_VERSION = 1
DATA_PATH = Path(DATA_DIR)
LATEST_PATH = DATA_PATH / "latest"
DERIVED_PATH = DATA_PATH / "derived"
SEASONS_PATH = DATA_PATH / "seasons"
REPORTS_PATH = DATA_PATH.parent / "reports" / "daily"
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
    excluded_dirs = {"latest", "derived", "archive", "_reports", "seasons"}
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


def load_latest_payload(namespace: str, season: Optional[str] = None, base_path: Optional[Path] = None) -> Optional[Any]:
    latest = base_path or LATEST_PATH
    if season:
        path = latest / season / f"{namespace}.json"
    else:
        path = latest / f"{namespace}.json"
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


def generate_derived(
    current_season: str,
    generated_at: str,
    current_build_id: str,
    output_dir: Optional[Path] = None,
    latest_base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    season_dir = output_dir or (DERIVED_PATH / current_season)
    season_dir.mkdir(parents=True, exist_ok=True)

    career = load_latest_payload("player-career-wuyan", base_path=latest_base_path)
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

    abilities = load_latest_payload("player-abilities", current_season, base_path=latest_base_path) or {}
    write_json(season_dir / "abilities.json", derived_payload(current_season, generated_at, current_build_id, abilities))

    ranking = load_latest_payload("all-player-stats", current_season, base_path=latest_base_path) or {}
    write_json(season_dir / "ranking.json", derived_payload(current_season, generated_at, current_build_id, ranking))

    hero_summary = load_latest_payload("player-hero-summary", current_season, base_path=latest_base_path) or {}
    hero_battles = load_latest_payload("player-hero-battles", current_season, base_path=latest_base_path) or {}
    hero_win_rate = load_latest_payload("hero-win-rate", current_season, base_path=latest_base_path) or {}
    heroes = {
        "summary": unwrap_data(hero_summary) if hero_summary else [],
        "battles": hero_battles.get("heroes", {}) if isinstance(hero_battles, dict) else {},
        "league_win_rate": unwrap_data(hero_win_rate) if hero_win_rate else [],
    }
    write_json(season_dir / "heroes.json", derived_payload(current_season, generated_at, current_build_id, heroes))

    win = load_latest_payload("player-win-stats", current_season, base_path=latest_base_path) or {}
    lose = load_latest_payload("player-lose-stats", current_season, base_path=latest_base_path) or {}
    win_lose = {
        "win": first_item(win),
        "lose": first_item(lose),
        "win_source": win,
        "lose_source": lose,
    }
    write_json(season_dir / "win-lose.json", derived_payload(current_season, generated_at, current_build_id, win_lose))

    # --- Analysis modules: compute metrics, trends, growth path ---
    metrics = None
    trends_data = None
    growth_path_data = None

    try:
        # Load previous abilities snapshot for volatility detection
        prev_abilities = None
        abilities_timeline = sorted(DATA_PATH.glob(f"player-abilities.{current_season}.*.json"))
        if len(abilities_timeline) >= 2:
            prev_abilities = load_json(abilities_timeline[-2])

        # Build cross-season hero usage for maturity classification
        all_season_heroes: Dict[str, Dict[str, int]] = {}
        for path in sorted(DATA_PATH.glob("player-hero-summary.*.*.json")):
            info = parse_data_file(path)
            ns_season = info.get("season")
            if ns_season and ns_season != current_season:
                data = load_json(path)
                inner = unwrap_data(data)
                if isinstance(inner, list):
                    hero_map = {}
                    for h in inner:
                        name = h.get("hero_name", "")
                        matches = h.get("total_matches", 0)
                        if name:
                            hero_map[name] = matches
                    all_season_heroes[ns_season] = hero_map

        metrics = compute_metrics(
            overview=overview,
            heroes=heroes,
            abilities_data=abilities,
            ranking_data=ranking,
            win_lose=win_lose,
            all_season_heroes=all_season_heroes,
            prev_abilities_data=prev_abilities,
            season=current_season,
        )

        # Compute trends
        trends_data = compute_trends(current_season)
        write_json(
            season_dir / "trend-summary.json",
            derived_payload(current_season, generated_at, current_build_id, trends_data),
        )

        # Generate growth path
        abilities_metrics = metrics.get("abilities", {})
        growth_path_data = generate_growth_path(
            overview=overview,
            heroes=heroes,
            abilities_metrics=abilities_metrics,
            season=current_season,
        )
        write_json(
            season_dir / "growth-path.json",
            derived_payload(current_season, generated_at, current_build_id, growth_path_data),
        )

        # Merge maturity labels back into heroes.json
        maturity_map = {}
        for h in metrics.get("hero_pool", {}).get("heroes", []):
            maturity_map[h.get("hero_name", "")] = h.get("maturity", "")
        if maturity_map:
            for h in heroes.get("summary", []):
                name = h.get("hero_name", "")
                if name in maturity_map:
                    h["maturity"] = maturity_map[name]
            write_json(season_dir / "heroes.json", derived_payload(current_season, generated_at, current_build_id, heroes))

    except Exception as e:
        print(f"[WARN] analysis modules failed: {e}")
        import traceback
        traceback.print_exc()

    # --- Generate rule insights (enhanced with metrics if available) ---
    insights = generate_rule_insights(
        current_season, overview, heroes, win_lose,
        metrics=metrics, growth_path=growth_path_data,
    )
    write_json(season_dir / "insights.json", derived_payload(current_season, generated_at, current_build_id, insights))

    return {
        "metrics": metrics,
        "trends": trends_data,
        "growth_path": growth_path_data,
    }


def parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace("%", ""))
    except ValueError:
        return None


def generate_rule_insights(
    season: str,
    overview: Dict[str, Any],
    heroes: Dict[str, Any],
    win_lose: Dict[str, Any],
    metrics: Optional[Dict[str, Any]] = None,
    growth_path: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate structured rule-based insights with per-section analysis.

    Falls back to legacy flat highlights if metrics are not provided.
    """
    # --- Legacy fallback (when called without metrics) ---
    if metrics is None:
        highlights = []
        summary = overview.get("career_summary", {})
        total = summary.get("total_battles", 0)
        if total:
            highlights.append(f"无言生涯已累计 {total} 小局，数据持续积累中")
        hero_list = heroes.get("summary") or []
        if hero_list:
            hero_count = len(hero_list)
            highlights.append(f"{season} 本赛季使用 {hero_count} 个英雄")
            top = sorted(hero_list, key=lambda h: h.get("total_matches") or 0, reverse=True)[0]
            highlights.append(f"使用最多英雄：{top.get('hero_name')}，出场 {top.get('total_matches')} 次")
        if total and total < 10:
            highlights.append("当前样本量较小，更适合观察上场机会和英雄池扩展")
        if not highlights:
            highlights.append("数据持续积累中，更多趋势洞察将在样本增加后生成")
        return {
            "headline": highlights[0],
            "highlights": highlights,
            "risk_notes": ["自动规则生成，仅供前端展示和人工复核，不作为最终赛训结论"],
        }

    # --- Structured insights with metrics ---
    hero_pool = metrics.get("hero_pool", {})
    wl_diff = metrics.get("win_lose_diff", {})
    abilities = metrics.get("abilities", {})
    ranking = metrics.get("ranking", {})
    team = metrics.get("team_structure", {})
    gp = growth_path or {}

    current_battles = team.get("current_season_battles", 0)
    hero_count = hero_pool.get("total_heroes", 0)

    def _confidence(sample_size: int) -> str:
        if sample_size <= 5:
            return "low"
        elif sample_size <= 10:
            return "medium"
        return "high"

    sections = []

    # --- Hero Pool section ---
    maturity_counts = hero_pool.get("maturity_counts", {})
    hero_evidence = []
    if hero_count:
        hero_evidence.append(f"本赛季使用 {hero_count} 个英雄，共 {current_battles} 局")
    for mat, label in [("core", "核心"), ("rotation", "轮换"), ("trial", "尝试")]:
        count = maturity_counts.get(mat, 0)
        if count:
            hero_evidence.append(f"{label}层级英雄 {count} 个")
    hhi = hero_pool.get("concentration", 0)
    if hhi > 0.5:
        hero_evidence.append(f"英雄使用集中度较高（HHI={hhi:.2f}）")
    elif hhi > 0:
        hero_evidence.append(f"英雄使用较为分散（HHI={hhi:.2f}）")

    sections.append({
        "id": "hero_pool",
        "title": "英雄池成熟度",
        "summary": f"当前样本中英雄池覆盖 {hero_count} 个英雄，" +
                   ("英雄使用较为集中。" if hhi > 0.5 else "英雄使用相对分散。" if hhi > 0 else ""),
        "conclusion_type": "fact" if current_battles >= 6 else "signal",
        "confidence": _confidence(current_battles),
        "sample_size": current_battles,
        "sample_unit": "games",
        "sample_scope": "current_season",
        "evidence": hero_evidence,
        "risk_notes": [f"本赛季仅 {current_battles} 局，英雄池评估受样本量限制"] if current_battles < 6 else [],
    })

    # --- Growth Path section ---
    growth_evidence = [gp.get("summary", "")] if gp.get("summary") else []
    milestones = gp.get("milestones", [])
    if milestones:
        growth_evidence.append(f"已记录 {len(milestones)} 个成长节点")
    signals = gp.get("signals", {})
    observed = signals.get("observed", [])
    watching = signals.get("watching", [])
    if observed:
        growth_evidence.append(f"已出现 {len(observed)} 个能力信号")
    if watching:
        growth_evidence.append(f"正在观察 {len(watching)} 个能力维度")

    sections.append({
        "id": "growth_path",
        "title": "成长路径观察",
        "summary": gp.get("summary", "成长路径数据生成中。"),
        "conclusion_type": "signal",
        "confidence": _confidence(current_battles),
        "sample_size": current_battles,
        "sample_unit": "games",
        "sample_scope": "current_season",
        "evidence": [e for e in growth_evidence if e],
        "risk_notes": gp.get("risk_notes", []),
    })

    # --- Abilities section ---
    above = abilities.get("above_avg", [])
    below = abilities.get("below_avg", [])
    volatile = abilities.get("volatile", [])
    pos_rank = abilities.get("position_rank")
    overall_rank = abilities.get("overall_rank")
    ability_evidence = []
    if pos_rank:
        ability_evidence.append(f"位置排名：第 {pos_rank} 名")
    if overall_rank:
        ability_evidence.append(f"总排名：第 {overall_rank} 名")
    if above:
        ability_evidence.append(f"高于同位置均值维度：{len(above)} 个")
    if below:
        ability_evidence.append(f"低于同位置均值维度：{len(below)} 个")
    if volatile:
        ability_evidence.append(f"近期波动较大维度：{len(volatile)} 个")

    sections.append({
        "id": "abilities",
        "title": "能力信号",
        "summary": f"当前能力评分 {abilities.get('overall_rating', '-')}，" +
                   (f"位置排名第 {pos_rank}。" if pos_rank else ""),
        "conclusion_type": "hypothesis" if current_battles > 10 else ("signal" if current_battles >= 3 else "fact"),
        "confidence": _confidence(current_battles),
        "sample_size": current_battles,
        "sample_unit": "games",
        "sample_scope": "current_season",
        "evidence": ability_evidence,
        "risk_notes": ["能力信号需要随更多上场样本持续验证"] if current_battles < 10 else [],
    })

    # --- Ranking section ---
    top_ranked = ranking.get("top_ranked", [])
    core_indicators = ranking.get("core_indicators", [])
    ranking_evidence = []
    if top_ranked:
        ranking_evidence.append(f"排名前列指标：{'、'.join(top_ranked)}")
    for ind in core_indicators[:5]:
        name = ind.get("name", "")
        rank = ind.get("rank")
        val = ind.get("value")
        if rank:
            ranking_evidence.append(f"{name}：排名第 {rank}（{val}）")

    sections.append({
        "id": "ranking",
        "title": "联盟排名",
        "summary": f"排名前列指标共 {len(top_ranked)} 项" +
                   (f"：{'、'.join(top_ranked)}" if top_ranked else "。"),
        "conclusion_type": "fact",
        "confidence": _confidence(current_battles),
        "sample_size": current_battles,
        "sample_unit": "games",
        "sample_scope": "current_season",
        "evidence": ranking_evidence,
        "risk_notes": ["排名数据受赛季初期样本量影响较大"] if current_battles < 6 else [],
    })

    # --- Win-Lose section ---
    has_lose = wl_diff.get("has_lose_data", False)
    wl_evidence = []
    if wl_diff.get("win_kda") is not None:
        wl_evidence.append(f"胜局平均 KDA: {wl_diff['win_kda']}")
    if has_lose and wl_diff.get("lose_kda") is not None:
        wl_evidence.append(f"败局平均 KDA: {wl_diff['lose_kda']}")
    low_metrics = wl_diff.get("low_metrics_in_losses", [])
    if low_metrics:
        wl_evidence.append(f"败局低位指标：{'、'.join(low_metrics)}")
    if not has_lose:
        wl_evidence.append("本赛季暂无败局数据")

    sections.append({
        "id": "win_lose",
        "title": "胜负差异",
        "summary": "胜局和败局的过程指标差异" +
                   ("，暂无败局数据可做对比。" if not has_lose else "。"),
        "conclusion_type": "fact" if not has_lose else "signal",
        "confidence": _confidence(current_battles),
        "sample_size": current_battles,
        "sample_unit": "games",
        "sample_scope": "current_season",
        "evidence": wl_evidence,
        "risk_notes": [] if has_lose else ["本赛季暂无败局样本，胜负差异无法计算"],
    })

    # --- Build headline and summary ---
    growth_stage = gp.get("growth_stage", "")
    career = overview.get("career_summary", {})
    total_battles = career.get("total_battles", 0)

    if current_battles < 6:
        headline = f"当前更适合观察无言的上场机会和英雄池扩展"
        global_summary = f"本赛季 {current_battles} 局，生涯累计 {total_battles} 局。基于有限样本，更适合观察英雄池扩展和队伍角色测试，不宜直接做稳定强弱判断。"
    else:
        headline = f"无言本赛季 {current_battles} 局，使用 {hero_count} 个英雄"
        global_summary = f"生涯累计 {total_battles} 局。本赛季英雄池覆盖 {hero_count} 个英雄，能力评分 {abilities.get('overall_rating', '-')}。"

    return {
        "headline": headline,
        "summary": global_summary,
        "growth_stage": growth_stage,
        "sections": sections,
        "updated_reason": "daily_fetch",
        "risk_notes": ["自动规则生成，仅供前端展示和人工复核，不作为最终赛训结论"],
    }


def list_available_seasons() -> list:
    """从 raw data 中扫描所有可用的赛季 ID。"""
    seasons = set()
    for path in iter_raw_json_files():
        info = parse_data_file(path)
        if info["season"]:
            seasons.add(info["season"])
    return sorted(seasons)


def _ensure_latest_for_season(season: str, generated_at: str, current_build_id: str) -> Path:
    """为指定赛季生成 latest 目录数据，返回 latest 根路径。

    目录结构与 generate_latest() 一致：
      latest/{season}/{namespace}.json  — 带赛季后缀的数据
      latest/player-career-wuyan.json   — 跨赛季通用数据
    """
    season_base = SEASONS_PATH / season
    season_latest = season_base / "latest"
    season_latest.mkdir(parents=True, exist_ok=True)

    # 带赛季后缀的数据 → latest/{season}/
    namespaces = {
        info["namespace"]
        for info in (parse_data_file(p) for p in iter_raw_json_files())
        if info["season"] == season and info["date"]
    }

    season_subdir = season_latest / season
    season_subdir.mkdir(parents=True, exist_ok=True)

    for namespace in sorted(namespaces):
        src = latest_file(namespace, season)
        if src:
            dst = season_subdir / f"{namespace}.json"
            shutil.copyfile(src, dst)

    # player-career-wuyan 无赛季后缀 → latest/
    career = latest_file("player-career-wuyan")
    if career:
        dst = season_latest / "player-career-wuyan.json"
        shutil.copyfile(career, dst)

    print(f"[INFO] latest 数据已准备：{season}（{len(namespaces)} 个命名空间）")
    return season_latest


def generate_season_manifest(
    season: str, generated_at: str, current_build_id: str,
    latest_dir: Path, derived_dir: Path,
) -> None:
    """生成赛季级 manifest，索引 latest 和 derived 下的所有文件。"""
    files = []
    for base, category in [(latest_dir, "latest"), (derived_dir, "derived")]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            stat = path.stat()
            rel = path.relative_to(base)
            files.append({
                "category": category,
                "file": str(rel).replace("\\", "/"),
                "hash": sha256_file(path),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).astimezone().isoformat(timespec="seconds"),
            })

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": generated_at,
        "build_id": current_build_id,
        "file_count": len(files),
        "files": files,
    }
    write_json(SEASONS_PATH / season / "manifest.json", manifest)
    print(f"[INFO] 赛季 manifest 已生成：{len(files)} 个文件")


def _print_artifact_manifest(season: str, season_derived_dir: Optional[Path] = None) -> None:
    """打印本次 post_process 生成的所有输出产物清单。"""
    artifacts: list[tuple[str, str]] = []

    # AI 日报
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    for report_path in sorted(REPORTS_PATH.glob(f"{today}*.md")):
        artifacts.append(("📄 AI 日报", str(report_path)))

    # Derived 目录产物
    derived_dir = season_derived_dir or (DERIVED_PATH / season)
    if derived_dir.exists():
        for path in sorted(derived_dir.glob("*.json")):
            size_kb = path.stat().st_size / 1024
            label = path.stem
            artifacts.append((f"📊 {label}", f"{path}  ({size_kb:.1f} KB)"))

    # 赛季 manifest
    manifest_path = SEASONS_PATH / season / "manifest.json"
    if manifest_path.exists():
        artifacts.append(("📋 赛季 manifest", str(manifest_path)))

    if not artifacts:
        print("[INFO] 本次运行未生成输出产物")
        return

    print(f"\n{'='*60}")
    print(f"📦 输出产物清单  season={season}")
    print(f"{'='*60}")
    for icon_label, detail in artifacts:
        print(f"  {icon_label:<20s}  {detail}")
    print(f"{'='*60}")
    print(f"  共 {len(artifacts)} 个产物\n")


def run(season_override: Optional[str] = None) -> Dict[str, Any]:
    generated_at = now_iso()
    current_build_id = build_id()
    current_info = get_current_season()
    current_season = current_info.get("current", "")
    if not current_season:
        raise RuntimeError("无法从 seasons-list 获取当前赛季")

    target_season = season_override or current_season
    if season_override:
        print(f"[INFO] 指定赛季模式：{target_season}（输出到 data/seasons/{target_season}/）")
    else:
        generate_manifest(generated_at, current_build_id)
        generate_latest(current_season, current_info, generated_at, current_build_id)

    # 历史赛季：输出到 data/seasons/{season}/
    season_latest_dir: Optional[Path] = None
    season_derived_dir: Optional[Path] = None

    if season_override:
        season_latest_dir = _ensure_latest_for_season(target_season, generated_at, current_build_id)
        season_derived_dir = SEASONS_PATH / target_season / "derived"

    analysis = generate_derived(
        target_season, generated_at, current_build_id,
        output_dir=season_derived_dir,
        latest_base_path=season_latest_dir if season_latest_dir else None,
    )

    metrics = analysis.get("metrics")
    trends = analysis.get("trends")
    growth_path = analysis.get("growth_path")

    # P1: AI insights (optional, best-effort)
    insights_path = (season_derived_dir / "insights.json") if season_derived_dir else (DERIVED_PATH / target_season / "insights.json")

    if metrics is None:
        print("[INFO] AI insights skipped: no metrics available")
    else:
        try:
            from src.analysis.ai_insights import generate_ai_insights
            rule_data = load_json(insights_path)
            generate_ai_insights(
                target_season, metrics, trends, growth_path,
                rule_insights=rule_data.get("data") if rule_data else None,
                generated_at=generated_at,
                build_id=current_build_id,
                output_dir=season_derived_dir,
            )
        except ImportError:
            print("[INFO] AI insights skipped: openai not installed")
        except Exception as e:
            print(f"[WARN] AI insights failed: {e}")

    # 历史赛季：生成赛季级 manifest
    if season_override and season_latest_dir and season_derived_dir:
        generate_season_manifest(target_season, generated_at, current_build_id, season_latest_dir, season_derived_dir)

    summary_parts = [f"season={target_season}", f"build_id={current_build_id}"]
    if metrics:
        hp = metrics.get("hero_pool", {})
        summary_parts.append(f"heroes={hp.get('total_heroes', 0)}")
    if trends:
        summary_parts.append(f"snapshots={trends.get('snapshots_available', 0)}")
    if growth_path:
        summary_parts.append(f"stage={growth_path.get('growth_stage', '?')}")

    print(f"[INFO] post_process 完成：{', '.join(summary_parts)}")

    # --- 输出产物清单 ---
    _print_artifact_manifest(target_season, season_derived_dir)

    return analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成发布数据视图（latest / derived / AI insights）")
    parser.add_argument(
        "-s", "--season",
        help="指定赛季 ID 生成 derived 数据（如 KPL2026S1），输出到 data/seasons/{season}/",
    )
    parser.add_argument(
        "--list-seasons",
        action="store_true",
        help="列出所有可用的赛季 ID 并退出",
    )
    args = parser.parse_args()

    if args.list_seasons:
        seasons = list_available_seasons()
        if seasons:
            print("可用赛季：")
            for s in seasons:
                print(f"  {s}")
        else:
            print("未找到任何赛季数据")
    else:
        run(season_override=args.season)
