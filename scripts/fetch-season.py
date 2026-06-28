#!/usr/bin/env python3
"""
fetch-season.py — 历史赛季原始数据抓取脚本

用法：
    python scripts/fetch-season.py --season KCC2025 [--force] [--dry-run]

功能：
1. 对指定赛季执行 raw audit
2. 只抓取 missing / empty_data / invalid_json 的 namespace
3. 使用赛季特定的选手名和战队名
4. 输出抓取 summary
"""

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from main import (
    audit_raw_season,
    fetch_season_data,
    print_audit_report,
    resolve_target_identity,
)
from src.storage.saver import KPLStorage


def main():
    parser = argparse.ArgumentParser(
        description="历史赛季原始数据抓取脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/fetch-season.py --season KCC2025 --dry-run
  python scripts/fetch-season.py --season KCC2026
  python scripts/fetch-season.py --season KCC2025 --force
        """,
    )
    parser.add_argument("--season", required=True, help="目标赛季 ID（如 KCC2025、KPL2026S1）")
    parser.add_argument("--force", action="store_true", help="强制重抓所有 namespace（忽略已有有效文件）")
    parser.add_argument("--dry-run", action="store_true", help="只输出 audit 报告，不实际抓取")
    args = parser.parse_args()

    season_id = args.season

    print("=" * 60)
    print(f"📥 历史赛季数据抓取: {season_id}")
    print("=" * 60)

    # Step 1: Raw audit
    print("\n[STEP 1] 执行 raw audit...")
    audit = audit_raw_season(season_id)
    print_audit_report(audit)

    summary = audit["summary"]
    if summary["valid"] == summary["total"]:
        print(f"\n✅ 所有 {summary['total']} 个 namespace 已有效，无需抓取")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] 以上为 audit 结果，实际运行将抓取以下 namespace:")
        for ns, info in sorted(audit["namespaces"].items()):
            if info["status"] != "valid":
                print(f"  → {ns} ({info['status']})")
        return 0

    # Step 2: 身份解析
    storage = KPLStorage()
    identity = resolve_target_identity(storage, season_id)

    # Step 3: 抓取
    print(f"\n[STEP 2] 开始抓取 {season_id}...")
    result = fetch_season_data(
        season_id,
        force=args.force,
        target_identity=identity,
    )

    # Step 4: 输出 summary
    print(f"\n{'=' * 60}")
    print(f"📊 抓取 Summary: {season_id}")
    print(f"{'=' * 60}")
    print(f"  成功: {result['success']}")
    print(f"  失败: {result['fail']}")
    print(f"  跳过: {result['skip']}")
    print(f"  选手: {identity['player_name']}")
    print(f"  战队: {identity['team_name']}")

    details = result.get("details", [])
    fetched = [d for d in details if d["result"] == "fetched"]
    skipped = [d for d in details if d["result"] == "skipped_valid"]
    failed = [d for d in details if d["result"] in ("failed", "error", "api_empty")]

    if fetched:
        print(f"\n  新抓取 ({len(fetched)}):")
        for d in fetched:
            print(f"    ✅ {d['namespace']}")
    if skipped:
        print(f"\n  已跳过 ({len(skipped)}):")
        for d in skipped:
            print(f"    ⏭️  {d['namespace']}")
    if failed:
        print(f"\n  失败/空数据 ({len(failed)}):")
        for d in failed:
            print(f"    ❌ {d['namespace']}: {d['result']}")

    print(f"{'=' * 60}\n")
    return 0 if result["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
