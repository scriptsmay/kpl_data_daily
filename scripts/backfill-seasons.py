#!/usr/bin/env python3
"""
backfill-seasons.py — 历史赛季 derived 数据补齐脚本

功能：
1. 读取 player-career-wuyan.json，提取选手参赛过的所有赛季 ID
2. 对比 data/seasons/ 下已有的 derived 数据
3. 对缺失的历史赛季运行 post_process.py -s {season}
4. 最后运行 post_process.py（不带 -s）重建当前赛季
5. 打印 summary
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
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
    parser = argparse.ArgumentParser(description="补齐历史赛季 derived 数据")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的操作，不实际运行")
    parser.add_argument("--force", action="store_true", help="强制重新生成已有赛季数据")
    parser.add_argument("--include-current", action="store_true", help="额外重建当前赛季 derived 数据")
    parser.add_argument("--season", help="只补齐指定赛季 ID（如 KPL2026S1）")
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

    # 3. 确定需要补齐的赛季
    if args.season:
        if args.season == current_season:
            targets = []
            args.include_current = True
        else:
            targets = [args.season]
    else:
        targets = [
            s for s in career_seasons
            if s != current_season and (s not in existing or args.force)
        ]

    if not targets and not args.include_current:
        print("\n✅ 所有赛季 derived 数据已存在，无需补齐")
        print("（如需重建当前赛季，使用 --include-current）")
        return 0

    if targets:
        print(f"\n需要补齐：{len(targets)} 个赛季")
        for s in targets:
            print(f"  → {s}")
    else:
        print("\n历史赛季无需补齐")

    # 4. 逐赛季生成
    success = 0
    failed = 0
    for s in targets:
        if run_post_process(s, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    # 5. 重建当前赛季
    if args.include_current and current_season:
        print(f"\n重建当前赛季：{current_season}")
        if run_post_process(dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    # 6. Summary
    print(f"\n{'=' * 60}")
    print(f"📊 补齐完成：成功 {success}，失败 {failed}")
    print(f"{'=' * 60}")

    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
