"""AI insights generation using OpenAI-compatible API.

Reads metrics, trends, and growth path data, calls an LLM to generate
structured Chinese insights, and writes ai-insights.json + daily report.

Configuration via environment variables:
  OPENAI_API_KEY   - Required. API key for the service.
  OPENAI_BASE_URL  - Optional. Custom endpoint (default: https://api.openai.com/v1)
  OPENAI_MODEL     - Optional. Model name (default: gpt-4o-mini)
"""

import json
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.storage.config import DATA_DIR


DATA_PATH = Path(DATA_DIR)
DERIVED_PATH = DATA_PATH / "derived"
REPORTS_PATH = DATA_PATH.parent / "reports" / "daily"

SCHEMA_VERSION = 1
PROMPT_VERSION = "ai-insights-v2-20260627"

# Required fields per section
REQUIRED_SECTION_FIELDS = [
    "id", "title", "summary", "conclusion_type",
    "confidence", "sample_size", "sample_unit", "sample_scope",
    "evidence", "risk_notes",
]

VALID_SECTION_IDS = [
    "hero_pool", "growth_path", "abilities",
    "ranking", "win_lose", "team_structure",
]

VALID_CONCLUSION_TYPES = ["fact", "signal", "hypothesis"]
VALID_CONFIDENCE = ["low", "medium", "high"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _build_id() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S%z")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _stable_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_ai_output(output: Dict[str, Any]) -> list:
    """Validate the AI-generated output against the schema.

    Returns a list of error messages. Empty list means valid.
    """
    errors = []

    if not output.get("headline"):
        errors.append("missing headline")
    if not output.get("summary"):
        errors.append("missing summary")

    sections = output.get("sections", [])
    if not isinstance(sections, list) or not (3 <= len(sections) <= 6):
        errors.append(f"sections must be a list of 3-6, got {len(sections) if isinstance(sections, list) else type(sections)}")
    else:
        for i, s in enumerate(sections):
            if not isinstance(s, dict):
                errors.append(f"sections[{i}] must be object")
                continue
            for field in REQUIRED_SECTION_FIELDS:
                if field not in s:
                    errors.append(f"sections[{i}] missing field: {field}")
            if s.get("id") not in VALID_SECTION_IDS:
                errors.append(f"sections[{i}] invalid id: {s.get('id')}")
            if s.get("conclusion_type") not in VALID_CONCLUSION_TYPES:
                errors.append(f"sections[{i}] invalid conclusion_type: {s.get('conclusion_type')}")
            if s.get("confidence") not in VALID_CONFIDENCE:
                errors.append(f"sections[{i}] invalid confidence: {s.get('confidence')}")
            if not isinstance(s.get("evidence"), list):
                errors.append(f"sections[{i}] evidence must be list")
            if not isinstance(s.get("risk_notes"), list):
                errors.append(f"sections[{i}] risk_notes must be list")

    return errors


def _data_completeness_warnings(metrics: Dict[str, Any]) -> list:
    """Return warnings when key metric groups are internally inconsistent."""
    warnings = []
    team = metrics.get("team_structure", {})
    hero_pool = metrics.get("hero_pool", {})
    abilities = metrics.get("abilities", {})
    ranking = metrics.get("ranking", {})

    current_battles = team.get("current_season_battles", 0) or 0
    hero_count = hero_pool.get("total_heroes", 0) or 0
    ability_scores = abilities.get("scores", {}) or {}
    ranking_indicators = ranking.get("core_indicators", []) or []

    if current_battles > 0 and hero_count == 0:
        warnings.append(f"本赛季已有 {current_battles} 局，但英雄池数据为空")
    if current_battles > 0 and not ability_scores:
        warnings.append(f"本赛季已有 {current_battles} 局，但能力画像数据为空")
    if current_battles > 0 and not ranking_indicators:
        warnings.append(f"本赛季已有 {current_battles} 局，但联盟排名数据为空")

    return warnings


def _fallback_output(
    season: str,
    metrics: Dict[str, Any],
    reason: str,
    warnings: Optional[list] = None,
    rule_insights: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic safe output when AI output is unavailable or unsafe."""
    warnings = warnings or []
    team = metrics.get("team_structure", {})
    current_battles = team.get("current_season_battles", 0) or 0
    hero_count = metrics.get("hero_pool", {}).get("total_heroes", 0) or 0
    rule_sections = rule_insights.get("sections", []) if isinstance(rule_insights, dict) else []

    if warnings:
        headline = f"{season} 数据完整性不足，暂不生成竞技判断"
        summary = "；".join(warnings[:3]) + "。请先检查采集或派生数据后再解读。"
        sections = [
            {
                "id": "growth_path",
                "title": "数据完整性",
                "summary": summary,
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": current_battles,
                "sample_unit": "games",
                "sample_scope": "current_season",
                "evidence": warnings,
                "risk_notes": ["数据缺失时禁止生成英雄池、能力或竞技状态判断"],
            },
            {
                "id": "hero_pool",
                "title": "英雄池数据状态",
                "summary": f"当前英雄池记录为 {hero_count} 个，不能据此判断角色定位或英雄熟练度。",
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": hero_count,
                "sample_unit": "heroes",
                "sample_scope": "current_season",
                "evidence": [f"hero_count={hero_count}", f"current_battles={current_battles}"],
                "risk_notes": ["英雄池数据为空或不完整"],
            },
            {
                "id": "abilities",
                "title": "能力数据状态",
                "summary": "能力画像或排名数据不完整，暂不输出能力强弱相关结论。",
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": current_battles,
                "sample_unit": "games",
                "sample_scope": "current_season",
                "evidence": warnings,
                "risk_notes": ["等待完整能力画像和排名数据后再分析"],
            },
        ]
    elif rule_sections:
        headline = rule_insights.get("headline", f"{season} 使用规则洞察作为兜底")
        summary = rule_insights.get("summary", "AI 输出不可用，已回退到规则洞察。")
        sections = rule_sections[:6]
    else:
        headline = f"{season} AI 洞察暂不可用"
        summary = f"AI 输出未发布：{reason}"
        sections = [
            {
                "id": "growth_path",
                "title": "AI 输出状态",
                "summary": summary,
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": current_battles,
                "sample_unit": "games",
                "sample_scope": "current_season",
                "evidence": [reason],
                "risk_notes": ["等待下一次成功生成"],
            },
            {
                "id": "hero_pool",
                "title": "英雄池",
                "summary": "本次未生成 AI 英雄池解读。",
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": hero_count,
                "sample_unit": "heroes",
                "sample_scope": "current_season",
                "evidence": [reason],
                "risk_notes": ["AI 输出不可用"],
            },
            {
                "id": "ranking",
                "title": "排名",
                "summary": "本次未生成 AI 排名解读。",
                "conclusion_type": "fact",
                "confidence": "low",
                "sample_size": current_battles,
                "sample_unit": "games",
                "sample_scope": "current_season",
                "evidence": [reason],
                "risk_notes": ["AI 输出不可用"],
            },
        ]

    return {
        "headline": headline,
        "summary": summary,
        "growth_stage": (rule_insights or {}).get("growth_stage", ""),
        "sections": sections,
        "updated_reason": "fallback",
        "fallback_reason": reason,
    }


def _write_outputs(
    season: str,
    ai_output: Dict[str, Any],
    model: str,
    elapsed: float,
    generated_at: Optional[str],
    build_id: Optional[str],
    output_dir: Optional[Path],
    input_hash: str,
    skipped_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Write ai-insights.json and per-season daily report."""
    final_generated_at = generated_at or _now_iso()
    final_build_id = build_id or _build_id()

    ai_data = {
        **ai_output,
        "generated_at": final_generated_at,
        "build_id": final_build_id,
        "ai_elapsed_seconds": elapsed,
        "ai_model": model,
        "prompt_version": PROMPT_VERSION,
        "input_hash": input_hash,
    }
    if skipped_reason:
        ai_data["ai_skipped_reason"] = skipped_reason

    season_dir = output_dir or (DERIVED_PATH / season)
    season_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": final_generated_at,
        "build_id": final_build_id,
        "ai_elapsed_seconds": elapsed,
        "ai_model": model,
        "prompt_version": PROMPT_VERSION,
        "input_hash": input_hash,
        "data": ai_data,
    }
    if skipped_reason:
        payload["ai_skipped_reason"] = skipped_reason

    write_path = season_dir / "ai-insights.json"
    _write_json(write_path, payload)
    print(f"[INFO] AI insights written to {write_path}")

    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    report_content = generate_daily_report(ai_data, season)
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_PATH / f"{today}-{season}.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write(report_content)
        f.write("\n")
    print(f"[INFO] Daily report written to {report_path}")

    return ai_data


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_daily_report(ai_data: Dict[str, Any], season: str) -> str:
    """Generate a Markdown daily report from AI insights data."""
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    lines = [
        f"# KPL 赛事洞察 {today}",
        f"",
        f"赛季：{season}",
        f"",
        f"## 头条",
        f"",
        ai_data.get("headline", ""),
        f"",
        f"## 摘要",
        f"",
        ai_data.get("summary", ""),
        f"",
    ]

    growth_stage = ai_data.get("growth_stage", "")
    if growth_stage:
        lines.append(f"**成长阶段**：{growth_stage}")
        lines.append("")

    sections = ai_data.get("sections", [])
    if sections:
        lines.append("## 各主题洞察")
        lines.append("")
        for s in sections:
            lines.append(f"### {s.get('title', s.get('id', ''))}")
            lines.append("")
            lines.append(f"**结论类型**：{s.get('conclusion_type', '-')} | **置信度**：{s.get('confidence', '-')} | **样本量**：{s.get('sample_size', '-')} {s.get('sample_unit', '')}")
            lines.append("")
            lines.append(s.get("summary", ""))
            lines.append("")

            evidence = s.get("evidence", [])
            if evidence:
                lines.append("**证据**：")
                for e in evidence:
                    lines.append(f"- {e}")
                lines.append("")

            risk = s.get("risk_notes", [])
            if risk:
                lines.append("> **风险提示**：")
                for r in risk:
                    lines.append(f"> {r}")
                lines.append("")

    lines.append("---")
    ai_model = ai_data.get("ai_model", "")
    ai_elapsed = ai_data.get("ai_elapsed_seconds")
    meta_parts = [f"*自动生成于 {ai_data.get('generated_at', today)}*"]
    if ai_model:
        meta_parts.append(f"模型：{ai_model}")
    if ai_elapsed is not None:
        meta_parts.append(f"耗时：{ai_elapsed}s")
    lines.append(" | ".join(meta_parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_ai_insights(
    season: str,
    metrics: Dict[str, Any],
    trends: Optional[Dict[str, Any]] = None,
    growth_path: Optional[Dict[str, Any]] = None,
    rule_insights: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
    build_id: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Generate AI insights and write output files.

    Returns the AI output dict on success, None on failure.

    Raises:
        ImportError: If openai is not installed.
        EnvironmentError: If OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[INFO] AI insights skipped: OPENAI_API_KEY not set")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("[INFO] AI insights skipped: openai package not installed")
        return None

    base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    input_hash = _stable_hash({
        "season": season,
        "metrics": metrics,
        "trends": trends,
        "growth_path": growth_path,
        "rule_insights": rule_insights,
        "prompt_version": PROMPT_VERSION,
    })

    completeness_warnings = _data_completeness_warnings(metrics)
    if completeness_warnings:
        print(f"[WARN] AI skipped due to incomplete data: {completeness_warnings}")
        fallback = _fallback_output(
            season,
            metrics,
            reason="data_incomplete",
            warnings=completeness_warnings,
            rule_insights=rule_insights,
        )
        return _write_outputs(
            season,
            fallback,
            model=f"{model}:skipped",
            elapsed=0,
            generated_at=generated_at,
            build_id=build_id,
            output_dir=output_dir,
            input_hash=input_hash,
            skipped_reason="data_incomplete",
        )

    # Build prompt
    from src.analysis.prompts import SYSTEM_PROMPT, build_prompt
    user_prompt = build_prompt(season, metrics, trends, growth_path, rule_insights)

    # Call API
    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"[INFO] Calling AI: model={model}, base_url={base_url}")
    t0 = time.monotonic()
    response = None
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=180,
            )
            break
        except Exception as e:
            last_error = e
            if attempt >= 3:
                break
            wait_seconds = 2 ** attempt
            print(f"[WARN] AI call failed on attempt {attempt}, retrying in {wait_seconds}s: {e}")
            time.sleep(wait_seconds)

    elapsed = round(time.monotonic() - t0, 2)
    if response is None:
        print(f"[WARN] AI call failed after retries: {last_error}")
        fallback = _fallback_output(
            season,
            metrics,
            reason=f"api_error: {last_error}",
            rule_insights=rule_insights,
        )
        return _write_outputs(
            season,
            fallback,
            model=f"{model}:fallback",
            elapsed=elapsed,
            generated_at=generated_at,
            build_id=build_id,
            output_dir=output_dir,
            input_hash=input_hash,
            skipped_reason="api_error",
        )

    print(f"[INFO] AI response received in {elapsed}s")

    raw_content = response.choices[0].message.content
    if not raw_content:
        print("[WARN] AI returned empty content")
        fallback = _fallback_output(
            season,
            metrics,
            reason="empty_content",
            rule_insights=rule_insights,
        )
        return _write_outputs(
            season,
            fallback,
            model=f"{model}:fallback",
            elapsed=elapsed,
            generated_at=generated_at,
            build_id=build_id,
            output_dir=output_dir,
            input_hash=input_hash,
            skipped_reason="empty_content",
        )

    # Parse JSON
    try:
        ai_output = json.loads(raw_content)
    except json.JSONDecodeError as e:
        print(f"[WARN] AI output is not valid JSON: {e}")
        fallback = _fallback_output(
            season,
            metrics,
            reason=f"invalid_json: {e}",
            rule_insights=rule_insights,
        )
        return _write_outputs(
            season,
            fallback,
            model=f"{model}:fallback",
            elapsed=elapsed,
            generated_at=generated_at,
            build_id=build_id,
            output_dir=output_dir,
            input_hash=input_hash,
            skipped_reason="invalid_json",
        )

    # Validate
    errors = validate_ai_output(ai_output)
    if errors:
        print(f"[WARN] AI output validation errors: {errors}")
        fallback = _fallback_output(
            season,
            metrics,
            reason=f"validation_error: {'; '.join(errors)}",
            rule_insights=rule_insights,
        )
        return _write_outputs(
            season,
            fallback,
            model=f"{model}:fallback",
            elapsed=elapsed,
            generated_at=generated_at,
            build_id=build_id,
            output_dir=output_dir,
            input_hash=input_hash,
            skipped_reason="validation_error",
        )

    return _write_outputs(
        season,
        ai_output,
        model=model,
        elapsed=elapsed,
        generated_at=generated_at,
        build_id=build_id,
        output_dir=output_dir,
        input_hash=input_hash,
    )
