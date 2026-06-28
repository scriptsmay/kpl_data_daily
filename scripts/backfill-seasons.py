#!/usr/bin/env python3
"""
backfill-seasons.py — 历史赛季数据全流程补齐脚本

功能：
1. 读取 player-career-wuyan.json，提取选手参赛过的所有赛季 ID
2. 对每个赛季运行 raw audit
3. 对 raw 缺失或质量不合格的赛季 → 调用 fetch_season_data
4. 对历史赛季 raw 有变化或 derived 质量不合格的赛季 → 调用 post_process.py -s {season}
5. 对缺失/空 AI insights 的赛季 → 调用 generate_ai_insights（需 OPENAI_API_KEY）
6. 当前赛季 KPL2026S2 默认跳过，只在 --include-current 时运行
7. 输出完整 summary 和不可用接口清单
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

DATA_DIR = ROOT_DIR / "data"
SEASONS_DIR = DATA_DIR / "seasons"
LATEST_DIR = DATA_DIR / "latest"
CAREER_FILE = LATEST_DIR / "player-career-wuyan.json"
POST_PROCESS = ROOT_DIR / "post_process.py"

REQUIRED_DERIVED_FILES = {
    "overview.json",
    "abilities.json",
    "ranking.json",
    "heroes.json",
    "win-lose.json",
    "insights.json",
    "trend-summary.json",
    "growth-path.json",
    "ai-insights.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_career_season_ids() -> List[str]:
    """从 player-career-wuyan.json 提取选手参赛过的所有赛季 ID。"""
    if not CAREER_FILE.exists():
        print(f"[ERROR] 职业生涯数据不存在：{CAREER_FILE}")
        return []

    career = load_json(CAREER_FILE)
    data = career.get("data", career)
    season_ids: Set[str] = set()

    for s in data.get("season_stats", []):
        sid = s.get("season_id")
        if sid:
            season_ids.add(sid)

    for m in data.get("match_details", []):
        sid = m.get("season_id")
        if sid:
            season_ids.add(sid)

    return sorted(season_ids)


def get_current_season() -> Optional[str]:
    """从 current-season.json 读取当前赛季 ID。"""
    current_file = LATEST_DIR / "current-season.json"
    if not current_file.exists():
        return None
    data = load_json(current_file)
    return data.get("current")


def has_complete_season_outputs(season: str) -> bool:
    """检查历史赛季输出是否包含核心 derived、AI 洞察和 manifest。"""
    season_dir = SEASONS_DIR / season
    derived_dir = season_dir / "derived"
    if not derived_dir.exists() or not (season_dir / "manifest.json").exists():
        return False

    existing = {p.name for p in derived_dir.glob("*.json")}
    return REQUIRED_DERIVED_FILES.issubset(existing)


def get_complete_derived_seasons() -> Set[str]:
    """扫描 data/seasons/ 下已完整生成的历史赛季 ID。"""
    seasons: Set[str] = set()
    if SEASONS_DIR.exists():
        for d in SEASONS_DIR.iterdir():
            if d.is_dir() and has_complete_season_outputs(d.name):
                seasons.add(d.name)
    return seasons


def audit_raw_season(season_id: str) -> Dict[str, Any]:
    """对指定赛季执行 raw audit。"""
    from main import audit_raw_season as _audit
    return _audit(season_id, data_dir=str(DATA_DIR))


def fetch_season(season_id: str, force: bool = False) -> Dict[str, Any]:
    """调用 fetch_season_data 抓取指定赛季的原始数据。"""
    from main import fetch_season_data, resolve_target_identity
    from src.storage.saver import KPLStorage

    storage = KPLStorage()
    identity = resolve_target_identity(storage, season_id)
    return fetch_season_data(season_id, force=force, target_identity=identity)


def run_post_process(season: Optional[str] = None, dry_run: bool = False) -> bool:
    """运行 post_process.py，返回是否成功。"""
    cmd = [sys.executable, str(POST_PROCESS)]
    if season:
        cmd.extend(["-s", season])

    label = season or "当前赛季"
    if dry_run:
        print(f"  [DRY] 将执行：{' '.join(cmd)}")
        return True

    print(f"  生成 {label} 数据...")
    result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] {label} 生成失败：{result.stderr[:500]}")
        if result.stdout:
            print(f"  [STDOUT] {result.stdout[-500:]}")
        return False
    # 只输出关键行
    for line in result.stdout.splitlines():
        if line.startswith("[INFO] post_process 完成") or line.startswith("[INFO] 赛季 manifest"):
            print(f"  {line}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="历史赛季数据全流程补齐脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式说明：
  默认模式：fetch + derived + AI insights 全流程
  --fetch-only：只抓取原始数据
  --derived-only：只生成 derived（跳过抓取）
  --ai-only：只生成 AI insights
  --with-ai：全流程包含 AI 分析（默认不含）
  --audit-only：只输出 raw / derived 质量审计

示例：
  python scripts/backfill-seasons.py --dry-run
  python scripts/backfill-seasons.py --audit-only
  python scripts/backfill-seasons.py --fetch-only --season KCC2025
  python scripts/backfill-seasons.py --derived-only
  python scripts/backfill-seasons.py --with-ai
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的操作，不实际运行")
    parser.add_argument("--force", action="store_true", help="强制重新抓取/生成已有数据")
    parser.add_argument("--include-current", action="store_true", help="额外处理当前进行中赛季 KPL2026S2")
    parser.add_argument("--season", help="只处理指定赛季 ID（如 KCC2025）")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fetch-only", action="store_true", help="只抓取原始数据，不生成 derived/AI")
    mode.add_argument("--derived-only", action="store_true", help="只生成 derived 数据（跳过抓取）")
    mode.add_argument("--ai-only", action="store_true", help="只生成 AI insights")
    mode.add_argument("--with-ai", action="store_true", help="全流程包含 AI 分析（默认不含）")
    mode.add_argument("--audit-only", action="store_true", help="只输出 raw / derived 质量审计")

    args = parser.parse_args()

    print("=" * 60)
    print("📊 历史赛季数据补齐脚本")
    print("=" * 60)

    # 1. 读取选手参赛赛季
    career_seasons = get_career_season_ids()
    current_season = get_current_season()

    print(f"\n选手参赛赛季：{len(career_seasons)} 个")
    for s in career_seasons:
        tag = "（当前）" if s == current_season else ""
        print(f"  - {s} {tag}")

    if not career_seasons:
        print("[ERROR] 无赛季数据，退出")
        return 1

    # 2. 对比已有 derived
    existing = get_complete_derived_seasons()
    print(f"\n已完整生成 derived + AI 数据：{len(existing)} 个")
    for s in sorted(existing):
        print(f"  - {s}")

    # 3. 确定处理范围
    if args.season:
        if args.season == current_season:
            targets = []
            args.include_current = True
        else:
            targets = [args.season]
    elif args.audit_only:
        # audit 模式：审计所有非当前赛季
        targets = [s for s in career_seasons if s != current_season]
    else:
        targets = [
            s for s in career_seasons
            if s != current_season and (s not in existing or args.force)
        ]

    if not targets and not args.include_current:
        print("\n✅ 所有赛季数据已存在，无需补齐")
        print("（如需重建当前赛季，使用 --include-current）")
        return 0

    if targets:
        print(f"\n需要处理：{len(targets)} 个赛季")
        for s in targets:
            print(f"  → {s}")
    else:
        print("\n历史赛季无需补齐")

    # === AUDIT-ONLY 模式 ===
    if args.audit_only:
        print(f"\n{'=' * 60}")
        print("🔍 质量审计模式")
        print(f"{'=' * 60}")

        for s in targets:
            # Raw audit
            audit = audit_raw_season(s)
            summary = audit["summary"]
            print(f"\n  {s} raw: ✅{summary['valid']} ⚠️{summary['empty_data']} ❌{summary['missing']} 💥{summary['invalid_json']} 🚫{summary.get('api_unavailable', 0)}")

            # 列出不可用 API
            unavail = {ns: info for ns, info in audit["namespaces"].items() if info["status"] == "api_unavailable"}
            if unavail:
                for ns, info in sorted(unavail.items()):
                    print(f"    🚫 {ns}: {info['detail']}")

            # Derived audit
            season_dir = SEASONS_DIR / s / "derived"
            if season_dir.exists():
                existing_derived = {p.name for p in season_dir.glob("*.json")}
                missing = REQUIRED_DERIVED_FILES - existing_derived
                if missing:
                    print(f"  {s} derived: ❌ 缺失 {len(missing)}: {', '.join(sorted(missing))}")
                else:
                    print(f"  {s} derived: ✅ 完整（{len(existing_derived)} 文件）")
            else:
                print(f"  {s} derived: ❌ 目录不存在")

        return 0

    # === FETCH-ONLY 模式 ===
    if args.fetch_only:
        print(f"\n{'=' * 60}")
        print("📥 仅抓取原始数据模式")
        print(f"{'=' * 60}")

        success = 0
        failed = 0
        for s in targets:
            if args.dry_run:
                audit = audit_raw_season(s)
                summary = audit["summary"]
                print(f"  [DRY] {s}: 需抓取 {summary['missing'] + summary['empty_data'] + summary['invalid_json']} 个 namespace")
                continue

            result = fetch_season(s, force=args.force)
            if result["fail"] == 0:
                success += 1
            else:
                failed += 1

        if not args.dry_run:
            print(f"\n{'=' * 60}")
            print(f"📥 抓取完成：成功 {success}，失败 {failed}")
            print(f"{'=' * 60}")
        return 0 if failed == 0 else 1

    # === DERIVED-ONLY 模式 ===
    if args.derived_only:
        print(f"\n{'=' * 60}")
        print("📊 仅生成 derived 数据模式")
        print(f"{'=' * 60}")

        success = 0
        failed = 0
        for s in targets:
            if run_post_process(s, dry_run=args.dry_run):
                success += 1
            else:
                failed += 1

        if not args.dry_run:
            print(f"\n{'=' * 60}")
            print(f"📊 生成完成：成功 {success}，失败 {failed}")
            print(f"{'=' * 60}")
        return 0 if failed == 0 else 1

    # === AI-ONLY 模式 ===
    if args.ai_only:
        print(f"\n{'=' * 60}")
        print("🤖 仅生成 AI insights 模式")
        print(f"{'=' * 60}")

        try:
            from src.analysis.ai_insights import generate_ai_insights
        except ImportError:
            print("[ERROR] openai 未安装，无法生成 AI insights")
            return 1

        success = 0
        failed = 0
        for s in targets:
            derived_dir = SEASONS_DIR / s / "derived"
            if not derived_dir.exists():
                print(f"  [SKIP] {s}: derived 目录不存在，先运行 --derived-only")
                failed += 1
                continue

            if args.dry_run:
                print(f"  [DRY] 将为 {s} 生成 AI insights")
                continue

            try:
                from post_process import load_json, now_iso, build_id
                metrics_path = derived_dir / "insights.json"
                if metrics_path.exists():
                    rule_data = load_json(metrics_path)
                    generate_ai_insights(
                        s,
                        metrics=rule_data.get("data"),
                        trends=None,
                        growth_path=None,
                        rule_insights=rule_data.get("data"),
                        generated_at=now_iso(),
                        build_id=build_id(),
                        output_dir=derived_dir,
                    )
                    success += 1
                    print(f"  [OK] {s} AI insights 已生成")
                else:
                    print(f"  [SKIP] {s}: insights.json 不存在")
                    failed += 1
            except Exception as e:
                print(f"  [ERROR] {s}: {e}")
                failed += 1

        if not args.dry_run:
            print(f"\n{'=' * 60}")
            print(f"🤖 AI insights 完成：成功 {success}，失败 {failed}")
            print(f"{'=' * 60}")
        return 0 if failed == 0 else 1

    # === 默认模式：fetch + derived（不含 AI）===
    print(f"\n{'=' * 60}")
    print("🔄 全流程补齐模式" + ("（含 AI）" if args.with_ai else "（不含 AI）"))
    print(f"{'=' * 60}")

    success = 0
    failed = 0

    for s in targets:
        print(f"\n{'─' * 40}")
        print(f"处理赛季：{s}")
        print(f"{'─' * 40}")

        # Step 1: Fetch raw data
        if not args.dry_run:
            fetch_result = fetch_season(s, force=args.force)
            print(f"  抓取结果：成功 {fetch_result['success']}，失败 {fetch_result['fail']}，跳过 {fetch_result['skip']}")
        else:
            audit = audit_raw_season(s)
            summary = audit["summary"]
            print(f"  [DRY] 需抓取 {summary['missing'] + summary['empty_data'] + summary['invalid_json']} 个 namespace（{summary.get('api_unavailable', 0)} 个已确认不可用）")

        # Step 2: Generate derived
        if run_post_process(s, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    # 重建当前赛季
    if args.include_current and current_season:
        print(f"\n{'─' * 40}")
        print(f"重建当前赛季：{current_season}")
        print(f"{'─' * 40}")
        if run_post_process(dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"📊 补齐完成：成功 {success}，失败 {failed}")

    # 不可用接口清单（从结构化记录读取）
    all_unavailable = []
    for s in targets:
        audit = audit_raw_season(s)
        for ns, info in audit["namespaces"].items():
            if info["status"] == "api_unavailable":
                all_unavailable.append(f"{s}/{ns}: {info['detail']}")

    if all_unavailable:
        print(f"\n⚠️  不可用接口清单（已记录，不会重试）:")
        for item in all_unavailable:
            print(f"  - {item}")

    print(f"{'=' * 60}")

    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
