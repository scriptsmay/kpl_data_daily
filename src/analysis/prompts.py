"""Build structured prompts for AI insights generation.

Converts metrics, trends, and growth path data into readable Chinese summaries
that serve as input context for the LLM.
"""

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个 KPL（王者荣耀职业联赛）赛事数据分析专家。你的任务是基于提供的结构化数据摘要，为选手"无言"（KSG 战队，对抗路）生成中文赛事洞察。

## 核心规则

1. **只根据输入数据写结论**。不编造不存在的比赛、英雄、排名或数值。
2. **每条观点必须有对应 evidence**。evidence 必须能在输入数据中找到依据。
3. **样本量约束**：
   - sample_size < 3：只输出事实（conclusion_type = "fact"），不做趋势分析
   - sample_size 3-5：只输出观察信号（conclusion_type = "signal"），必须标注低样本
   - sample_size 6-10：允许弱趋势，conclusion_type 可以是 "signal"
   - sample_size > 10：可以输出相对稳定趋势，conclusion_type 可以是 "signal" 或 "hypothesis"
4. **语气约束**：
   - 不使用"必然""证明""状态崩盘""版本答案""状态下滑"等强判断词
   - 优先使用"从当前数据看""样本内呈现""需要结合后续比赛观察""值得关注"
5. **胜率约束**：不得基于胜率单独生成结论，胜率只能作为背景信息。
6. **成长路径优先**：优先描述上场机会、英雄池变化、战术角色和待观察问题，而非强弱判断。
7. **输出严格 JSON**，匹配提供的 schema。不要输出任何 JSON 之外的内容。

## 结论类型说明

- `fact`：纯事实陈述，例如"本赛季使用过 3 个英雄"
- `signal`：趋势信号，例如"当前样本中，胜局更常伴随较高参团率"
- `hypothesis`：待验证假设，例如"如果后续继续增加开团型英雄出场，可能说明队伍在测试其开团职责"

## 置信度说明

- `low`：sample_size < 3，或数据不完整
- `medium`：sample_size 3-10
- `high`：sample_size > 10，且数据稳定

## 输出 schema

```json
{
  "headline": "一句话概括当前最值得关注的观察",
  "summary": "1-2 句全局摘要",
  "growth_stage": "机会积累期|英雄池测试期|稳定轮换期",
  "sections": [
    {
      "id": "hero_pool|growth_path|abilities|ranking|win_lose|team_structure",
      "title": "中文标题",
      "summary": "该主题的核心观察，1-2 句",
      "conclusion_type": "fact|signal|hypothesis",
      "confidence": "low|medium|high",
      "sample_size": 0,
      "sample_unit": "games|matches|heroes",
      "sample_scope": "current_season|recent_7_days|career",
      "evidence": ["证据1", "证据2"],
      "risk_notes": ["风险提示"]
    }
  ],
  "updated_reason": "daily_fetch"
}
```

## 重要提示

- sections 数量至少 3 个，最多 6 个
- 每个 section 的 id 必须是以下之一：hero_pool, growth_path, abilities, ranking, win_lose, team_structure
- evidence 中的数值必须与输入数据一致，不得四舍五入或修改
- risk_notes 在样本量低或数据不完整时必须出现
- growth_stage 必须与输入数据中的 growth_stage 保持一致"""


# ---------------------------------------------------------------------------
# Data formatting helpers
# ---------------------------------------------------------------------------

def _format_hero_pool(metrics: Dict[str, Any]) -> str:
    hp = metrics.get("hero_pool", {})
    lines = [f"## 英雄池数据"]
    lines.append(f"- 英雄总数：{hp.get('total_heroes', 0)}")
    lines.append(f"- 总出场局数：{hp.get('total_matches', 0)}")
    lines.append(f"- 集中度（HHI）：{hp.get('concentration', 0):.4f}")

    maturity = hp.get("maturity_counts", {})
    if maturity:
        lines.append(f"- 成熟度分布：")
        for m, label in [("core", "核心"), ("rotation", "轮换"), ("trial", "尝试"), ("watch_only", "待观察")]:
            count = maturity.get(m, 0)
            if count:
                lines.append(f"  - {label}：{count} 个")

    heroes = hp.get("heroes", [])
    if heroes:
        lines.append(f"- 英雄明细：")
        for h in heroes[:10]:
            wr = f"{h['win_rate']}%" if h.get("win_rate") is not None else "-"
            maturity_label = {
                "core": "核心",
                "rotation": "轮换观察",
                "trial": "尝试样本",
                "watch_only": "待观察",
            }.get(h.get("maturity"), h.get("maturity", "-"))
            historical = h.get("historical_usage") or {}
            history_text = ""
            if historical:
                history_text = (
                    f"，历史 {historical.get('prior_seasons', 0)} 个赛季、"
                    f"{historical.get('prior_matches', 0)} 局"
                )
            lines.append(
                f"  - {h['hero_name']}：出场 {h['total_matches']} 局，"
                f"胜率 {wr}，成熟度 {maturity_label}{history_text}"
            )

    return "\n".join(lines)


def _format_win_lose(metrics: Dict[str, Any]) -> str:
    wl = metrics.get("win_lose_diff", {})
    lines = [f"## 胜负差异数据"]
    lines.append(f"- 有败局数据：{'是' if wl.get('has_lose_data') else '否'}")

    pairs = [
        ("KDA", "win_kda", "lose_kda"),
        ("分均伤害", "win_dpm", "lose_dpm"),
        ("分均承伤", "win_dtpm", "lose_dtpm"),
        ("场均经济", "win_gold", "lose_gold"),
        ("场均死亡", "win_deaths", "lose_deaths"),
    ]

    for label, w, l in pairs:
        wv = wl.get(w)
        lv = wl.get(l)
        if wv is not None:
            line = f"- 胜局{label}：{wv}"
            if wl.get("has_lose_data") and lv is not None:
                line += f"，败局{label}：{lv}"
            lines.append(line)

    low = wl.get("low_metrics_in_losses", [])
    if low:
        lines.append(f"- 败局低位指标：{'、'.join(low)}")

    return "\n".join(lines)


def _format_abilities(metrics: Dict[str, Any]) -> str:
    ab = metrics.get("abilities", {})
    lines = [f"## 能力画像数据"]
    lines.append(f"- 综合评分：{ab.get('overall_rating', '-')}")
    lines.append(f"- 总排名：第 {ab.get('overall_rank', '-')} 名")
    lines.append(f"- 位置排名：第 {ab.get('position_rank', '-')} 名（{ab.get('player_position', '-')}）")

    scores = ab.get("scores", {})
    if scores:
        lines.append(f"- 各维度评分：")
        dim_labels = {
            "damage_output": "伤害输出", "teamfight": "团战", "initiation": "开团",
            "early_game": "前期", "mid_game": "中期", "late_game": "后期",
            "map_control": "地图控制", "invasion_ability": "入侵",
            "support_ability": "支援", "economy": "经济", "tankiness": "坦度",
            "durability": "生存",
        }
        for dim, val in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            label = dim_labels.get(dim, dim)
            lines.append(f"  - {label}：{val}")

    above = ab.get("above_avg", [])
    below = ab.get("below_avg", [])
    if above:
        lines.append(f"- 高于同位置均值维度：{len(above)} 个")
    if below:
        lines.append(f"- 低于同位置均值维度：{len(below)} 个")

    volatile = ab.get("volatile", [])
    if volatile:
        lines.append(f"- 近期波动较大维度：{volatile}")

    return "\n".join(lines)


def _format_ranking(metrics: Dict[str, Any]) -> str:
    rk = metrics.get("ranking", {})
    lines = [f"## 联盟排名数据"]

    top = rk.get("top_ranked", [])
    if top:
        lines.append(f"- 排名前列指标（前 3）：{'、'.join(top)}")

    indicators = rk.get("core_indicators", [])
    if indicators:
        lines.append(f"- 核心指标排名：")
        for ind in indicators[:8]:
            name = ind.get("name", "")
            val = ind.get("value", "")
            rank = ind.get("rank", "")
            lines.append(f"  - {name}：{val}（排名第 {rank}）")

    return "\n".join(lines)


def _format_growth_path(growth_path: Dict[str, Any]) -> str:
    lines = [f"## 成长路径数据"]
    lines.append(f"- 成长阶段：{growth_path.get('growth_stage', '-')}")
    lines.append(f"- 摘要：{growth_path.get('summary', '-')}")

    milestones = growth_path.get("milestones", [])
    if milestones:
        lines.append(f"- 里程碑（{len(milestones)} 个）：")
        for m in milestones[:8]:
            lines.append(f"  - {m.get('type', '')}：{m.get('description', '')}")

    signals = growth_path.get("signals", {})
    for key, label in [("observed", "已出现"), ("watching", "正在观察"), ("insufficient", "样本不足")]:
        items = signals.get(key, [])
        if items:
            lines.append(f"- {label}信号（{len(items)} 个）：")
            for item in items[:5]:
                lines.append(f"  - {item}")

    risk = growth_path.get("risk_notes", [])
    if risk:
        lines.append(f"- 风险提示：")
        for r in risk:
            lines.append(f"  - {r}")

    return "\n".join(lines)


def _format_trends(trends: Dict[str, Any]) -> str:
    lines = [f"## 趋势数据"]
    lines.append(f"- 可用快照数：{trends.get('snapshots_available', 0)}")
    lines.append(f"- 参考日期：{trends.get('reference_date', '-')}")

    trend_data = trends.get("trends", {})
    for ns, label in [("hero_pool", "英雄池"), ("abilities", "能力"), ("ranking", "排名")]:
        ns_trends = trend_data.get(ns, {})
        if ns_trends:
            lines.append(f"### {label}趋势")
            for window, data in ns_trends.items():
                snaps = data.get("snapshots", 0)
                lines.append(f"- {window}：{snaps} 个快照")
                if data.get("date_range"):
                    lines.append(f"  - 日期范围：{data['date_range']}")
                # Hero pool specific
                delta = data.get("hero_count_delta")
                if delta is not None:
                    lines.append(f"  - 英雄数量变化：{delta:+d}")
                new = data.get("new_heroes", [])
                if new:
                    lines.append(f"  - 新增英雄：{', '.join(new)}")
                # Ability specific
                gain = data.get("biggest_gain", {})
                drop = data.get("biggest_drop", {})
                if gain:
                    for k, v in gain.items():
                        lines.append(f"  - 最大增长：{k} {v:+.1f}")
                if drop:
                    for k, v in drop.items():
                        lines.append(f"  - 最大下降：{k} {v:+.1f}")

    anomalies = trends.get("anomalies", [])
    if anomalies:
        lines.append(f"- 异常标记：")
        for a in anomalies:
            lines.append(f"  - {a}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main prompt builder
# ---------------------------------------------------------------------------

def build_prompt(
    season: str,
    metrics: Dict[str, Any],
    trends: Optional[Dict[str, Any]],
    growth_path: Optional[Dict[str, Any]],
    rule_insights: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the user prompt with all data summaries.

    Returns a formatted string ready to be sent to the LLM.
    """
    parts = [
        f"# KPL 赛事洞察数据输入",
        f"",
        f"赛季：{season}",
        f"",
    ]

    # Growth stage context
    if growth_path:
        parts.append(f"当前成长阶段：{growth_path.get('growth_stage', '-')}")
        parts.append("")

    # Rule insights as baseline
    if rule_insights:
        parts.append("## 规则洞察基线（你的输出应在此基础上提供更丰富的解释）")
        parts.append(f"- headline: {rule_insights.get('headline', '-')}")
        parts.append(f"- summary: {rule_insights.get('summary', '-')}")
        sections = rule_insights.get("sections", [])
        for s in sections:
            parts.append(f"- {s.get('title', s.get('id', ''))}: {s.get('summary', '')}")
        parts.append("")

    # Detailed data
    parts.append(_format_hero_pool(metrics))
    parts.append("")
    parts.append(_format_win_lose(metrics))
    parts.append("")
    parts.append(_format_abilities(metrics))
    parts.append("")
    parts.append(_format_ranking(metrics))
    parts.append("")

    if growth_path:
        parts.append(_format_growth_path(growth_path))
        parts.append("")

    if trends:
        parts.append(_format_trends(trends))
        parts.append("")

    parts.append("---")
    parts.append("请根据以上数据，按照系统提示中的 schema 输出严格 JSON。不要输出 JSON 之外的任何内容。")

    return "\n".join(parts)
