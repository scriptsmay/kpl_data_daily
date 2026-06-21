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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.storage.config import DATA_DIR


DATA_PATH = Path(DATA_DIR)
DERIVED_PATH = DATA_PATH / "derived"
REPORTS_PATH = DATA_PATH.parent / "reports" / "daily"

SCHEMA_VERSION = 1

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
    if not isinstance(sections, list) or len(sections) < 3:
        errors.append(f"sections must be a list of at least 3, got {len(sections) if isinstance(sections, list) else type(sections)}")
    else:
        for i, s in enumerate(sections):
            for field in REQUIRED_SECTION_FIELDS:
                if field not in s:
                    errors.append(f"sections[{i}] missing field: {field}")
            if s.get("id") not in VALID_SECTION_IDS:
                errors.append(f"sections[{i}] invalid id: {s.get('id')}")
            if s.get("conclusion_type") not in VALID_CONCLUSION_TYPES:
                errors.append(f"sections[{i}] invalid conclusion_type: {s.get('conclusion_type')}")
            if s.get("confidence") not in VALID_CONFIDENCE:
                errors.append(f"sections[{i}] invalid confidence: {s.get('confidence')}")

    return errors


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
    lines.append(f"*自动生成于 {ai_data.get('generated_at', today)}*")

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

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Build prompt
    from src.analysis.prompts import SYSTEM_PROMPT, build_prompt
    user_prompt = build_prompt(season, metrics, trends, growth_path, rule_insights)

    # Call API
    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"[INFO] Calling AI: model={model}, base_url={base_url}")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        timeout=60,
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        print("[WARN] AI returned empty content")
        return None

    # Parse JSON
    try:
        ai_output = json.loads(raw_content)
    except json.JSONDecodeError as e:
        print(f"[WARN] AI output is not valid JSON: {e}")
        return None

    # Validate
    errors = validate_ai_output(ai_output)
    if errors:
        print(f"[WARN] AI output validation errors: {errors}")
        # Still write the output but with warnings
        # Try to fix common issues
        for s in ai_output.get("sections", []):
            if s.get("conclusion_type") not in VALID_CONCLUSION_TYPES:
                s["conclusion_type"] = "signal"
            if s.get("confidence") not in VALID_CONFIDENCE:
                s["confidence"] = "medium"

    # Build final payload — use batch-consistent timestamps if provided
    final_generated_at = generated_at or _now_iso()
    final_build_id = build_id or _build_id()

    ai_data = {
        **ai_output,
        "generated_at": final_generated_at,
        "build_id": final_build_id,
    }

    # Write ai-insights.json
    season_dir = DERIVED_PATH / season
    season_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "season": season,
        "generated_at": final_generated_at,
        "build_id": final_build_id,
        "data": ai_data,
    }
    write_path = season_dir / "ai-insights.json"
    _write_json(write_path, payload)
    print(f"[INFO] AI insights written to {write_path}")

    # Write daily report
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    report_content = generate_daily_report(ai_data, season)
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_PATH / f"{today}.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write(report_content)
        f.write("\n")
    print(f"[INFO] Daily report written to {report_path}")

    return ai_data
