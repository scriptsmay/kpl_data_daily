"""Generate personal growth path data for the target player.

Focuses on opportunity tracking, hero pool evolution, role changes,
and ability signal classification rather than strength evaluation.
"""

from typing import Any, Dict, List, Optional

from src.analysis.metrics import ABILITY_DIMS


# ---------------------------------------------------------------------------
# Hero type / role inference
# ---------------------------------------------------------------------------

# Heuristic mapping based on common KPL hero archetypes for 对抗路
HERO_TYPE_MAP = {
    # 坦边 / 前排承伤
    "关羽": "坦边·开团",
    "白起": "坦边·承伤",
    "项羽": "坦边·承伤",
    "猪八戒": "坦边·承伤",
    "廉颇": "坦边·开团",
    "夏侯惇": "坦边·承伤",
    "苏烈": "坦边·开团",
    # 战边 / 输出型
    "马超": "战边·输出",
    "曹操": "战边·输出",
    "狂铁": "战边·持续",
    "夏洛特": "战边·持续",
    "司空震": "战边·输出",
    "芈月": "战边·单带",
    "吕布": "战边·输出",
    "达摩": "战边·开团",
    "老夫子": "战边·单带",
    "花木兰": "战边·刺杀",
    "蒙恬": "坦边·承伤",
    "姬小满": "战边·持续",
    "孙策": "战边·开团",
    "铠": "战边·持续",
    "哪吒": "战边·单带",
    "元歌": "战边·刺杀",
}


def _infer_role(hero_name: str) -> str:
    return HERO_TYPE_MAP.get(hero_name, "对抗路·未知")


def _infer_role_category(hero_name: str) -> str:
    full = _infer_role(hero_name)
    return full.split("·")[1] if "·" in full else "未知"


# ---------------------------------------------------------------------------
# Growth stage determination
# ---------------------------------------------------------------------------

def _determine_growth_stage(
    current_battles: int,
    hero_count: int,
) -> str:
    """Determine growth stage based on current season battles and hero count."""
    if current_battles <= 5:
        return "机会积累期"
    elif current_battles <= 15 and hero_count <= 4:
        return "英雄池测试期"
    elif current_battles > 15 and hero_count >= 5:
        return "稳定轮换期"
    elif current_battles > 15:
        return "英雄池测试期"
    else:
        return "机会积累期"


def _generate_stage_summary(stage: str, current_battles: int, hero_count: int) -> str:
    if stage == "机会积累期":
        return f"本赛季仅 {current_battles} 局上场，样本仍在积累阶段，更适合观察上场机会和英雄池扩展，不适合做稳定强弱判断。"
    elif stage == "英雄池测试期":
        return f"本赛季 {current_battles} 局，使用 {hero_count} 个英雄，队伍正在测试不同英雄和角色定位，英雄池覆盖是核心观察点。"
    elif stage == "稳定轮换期":
        return f"本赛季 {current_battles} 局，使用 {hero_count} 个英雄，已形成相对稳定的出场节奏和英雄池结构。"
    return f"本赛季 {current_battles} 局，{hero_count} 个英雄，持续积累比赛样本。"


# ---------------------------------------------------------------------------
# Milestone extraction
# ---------------------------------------------------------------------------

def _extract_milestones(
    overview: Dict[str, Any],
    heroes: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Extract career milestones from overview and hero data."""
    milestones = []

    player_info = overview.get("player_info", {})
    career = overview.get("career_summary", {})
    season_stats = overview.get("season_stats", [])

    # First appearance
    first_appear = player_info.get("first_appear_time", "")
    if first_appear:
        milestones.append({
            "type": "first_appear",
            "date": first_appear[:10] if len(first_appear) >= 10 else first_appear,
            "description": f"职业首秀，ID: {player_info.get('latest_nickname', '无言')}",
        })

    # Seasons covered
    seasons_covered = career.get("seasons_covered", [])
    for sc in seasons_covered:
        sid = sc.get("tournament_id", "")
        sname = sc.get("tournament_name", "")
        milestones.append({
            "type": "season_start",
            "date": "",
            "description": f"参赛赛季：{sname}（{sid}）",
        })

    # Career totals
    total_battles = career.get("total_battles", 0)
    if total_battles >= 100:
        milestones.append({
            "type": "career_milestone",
            "date": "",
            "description": f"生涯累计 {total_battles} 局",
        })

    mvp_count = career.get("mvp_count", 0)
    if mvp_count > 0:
        milestones.append({
            "type": "mvp",
            "date": "",
            "description": f"生涯累计 {mvp_count} 次 MVP",
        })

    # Recent match milestones (first win, etc.)
    recent_matches = overview.get("recent_matches", [])
    if recent_matches:
        for match in recent_matches:
            if match.get("is_win") and not any(m["type"] == "first_win" for m in milestones):
                milestones.append({
                    "type": "first_win",
                    "date": match.get("match_date", ""),
                    "description": f"首次胜利：{match.get('versus_info', '')}",
                })

    # Hero first usage from battles
    battles = heroes.get("battles", {})
    for hero_name, hero_data in battles.items():
        hero_battles = hero_data.get("battles", [])
        if hero_battles:
            first_battle = hero_battles[0]
            milestones.append({
                "type": "hero_first_use",
                "date": first_battle.get("match_date", ""),
                "description": f"首次使用 {hero_name}：{first_battle.get('versus_info', '')}",
            })

    return milestones


# ---------------------------------------------------------------------------
# Hero path (per-season)
# ---------------------------------------------------------------------------

def _build_hero_path(
    season_stats: List[Dict[str, Any]],
    overview: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build per-season hero usage path."""
    path = []

    # Current season from heroes data
    hero_stats = overview.get("hero_stats", [])
    if hero_stats:
        # hero_stats has career-level hero usage; group by season isn't available
        # So we use what we have from the current season heroes
        pass

    # Build from season_stats (battles per season)
    for ss in season_stats:
        season_id = ss.get("season_id", "")
        battles = ss.get("battles", 0)
        wins = ss.get("wins", 0)
        win_rate = ss.get("win_rate", "")

        path.append({
            "season": season_id,
            "battles": battles,
            "wins": wins,
            "win_rate": win_rate,
        })

    return path


# ---------------------------------------------------------------------------
# Role path (inferred from hero types)
# ---------------------------------------------------------------------------

def _build_role_path(
    heroes: Dict[str, Any],
    season_stats: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build role path from hero usage in current season."""
    summary = heroes.get("summary", [])
    if not summary:
        return []

    role_counts: Dict[str, int] = {}
    for h in summary:
        role_cat = _infer_role_category(h.get("hero_name", ""))
        matches = h.get("total_matches", 0)
        role_counts[role_cat] = role_counts.get(role_cat, 0) + matches

    return [{
        "roles": sorted(role_counts.keys()),
        "role_matches": role_counts,
    }]


# ---------------------------------------------------------------------------
# Ability signal classification
# ---------------------------------------------------------------------------

def _classify_signals(
    abilities_metrics: Dict[str, Any],
    sample_size: int,
) -> Dict[str, List[str]]:
    """Classify ability signals into observed / watching / insufficient."""
    observed: List[str] = []
    watching: List[str] = []
    insufficient: List[str] = []

    above_avg = abilities_metrics.get("above_avg", [])
    below_avg = abilities_metrics.get("below_avg", [])
    scores = abilities_metrics.get("scores", {})

    # DIM name to Chinese
    dim_labels = {
        "damage_output": "伤害输出",
        "teamfight": "团战能力",
        "initiation": "开团能力",
        "early_game": "前期能力",
        "mid_game": "中期能力",
        "late_game": "后期能力",
        "map_control": "地图控制",
        "invasion_ability": "入侵能力",
        "support_ability": "支援能力",
        "economy": "经济效率",
        "tankiness": "坦度",
        "durability": "生存能力",
    }

    for dim in ABILITY_DIMS:
        label = dim_labels.get(dim, dim)
        score = scores.get(dim)

        if sample_size < 6:
            # Low sample: everything is insufficient or watching
            if score is not None and score >= 85:
                watching.append(f"{label}（{score}分，样本不足需持续观察）")
            elif score is not None:
                insufficient.append(f"{label}（{score}分）")
        elif sample_size < 10:
            if dim in above_avg:
                observed.append(f"{label}高于同位置均值（{score}分）")
            elif score is not None and score >= 85:
                watching.append(f"{label}（{score}分）")
            else:
                insufficient.append(f"{label}（{score}分）")
        else:
            if dim in above_avg:
                observed.append(f"{label}高于同位置均值（{score}分）")
            elif dim in below_avg:
                watching.append(f"{label}低于同位置均值（{score}分）")
            else:
                insufficient.append(f"{label}（{score}分）")

    return {
        "observed": observed,
        "watching": watching,
        "insufficient": insufficient,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate(
    overview: Dict[str, Any],
    heroes: Dict[str, Any],
    abilities_metrics: Dict[str, Any],
    season: str,
) -> Dict[str, Any]:
    """Generate growth path data.

    Args:
        overview: Derived overview data (data section).
        heroes: Derived heroes data (data section).
        abilities_metrics: Computed abilities metrics from metrics.py.
        season: Current season ID.

    Returns:
        Growth path data dict matching growth-path.json data structure.
    """
    season_stats = overview.get("season_stats", [])
    hero_summary = heroes.get("summary", [])

    # Current season battles
    current_battles = 0
    for ss in season_stats:
        if ss.get("season_id") == season:
            current_battles = ss.get("battles", 0)
            break

    hero_count = len(hero_summary)

    # Growth stage
    growth_stage = _determine_growth_stage(current_battles, hero_count)
    summary = _generate_stage_summary(growth_stage, current_battles, hero_count)

    # Milestones
    milestones = _extract_milestones(overview, heroes)

    # Hero path
    hero_path = _build_hero_path(season_stats, overview)

    # Role path
    role_path = _build_role_path(heroes, season_stats)

    # Ability signals
    signals = _classify_signals(abilities_metrics, current_battles)

    # Risk notes
    risk_notes = []
    if current_battles < 6:
        risk_notes.append(f"本赛季仅 {current_battles} 局，所有趋势仅作为成长观察")
    if current_battles < 3:
        risk_notes.append("样本量极低，仅展示事实记录")
    risk_notes.append("胜率不单独作为评价依据")
    if hero_count <= 3:
        risk_notes.append(f"英雄池仅覆盖 {hero_count} 个英雄，角色定位仍在测试中")

    return {
        "player": "无言",
        "growth_stage": growth_stage,
        "summary": summary,
        "milestones": milestones,
        "hero_path": hero_path,
        "role_path": role_path,
        "signals": signals,
        "risk_notes": risk_notes,
    }
