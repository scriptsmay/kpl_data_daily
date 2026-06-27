#!/usr/bin/env python3
"""Raw file deduplication for kpl-data-daily.

Scans data/ for large-file namespaces, detects content-identical snapshots,
and replaces duplicates with a manifest reference to the first occurrence.

Usage:
    python dedup_raw.py              # dry-run: report what would change
    python dedup_raw.py --apply      # actually replace duplicates
    python dedup_raw.py --stats      # show dedup statistics only
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.storage.config import DATA_DIR

DATA_PATH = Path(DATA_DIR)
HASH_INDEX_PATH = DATA_PATH / ".hash-index.json"

# Namespaces eligible for dedup (large files with frequent identical snapshots)
DEDUP_NAMESPACES = {"season-records", "player-hero-battles", "win-affinity-analysis"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hash_index() -> Dict[str, Dict[str, str]]:
    """Load hash index: {namespace: {hash: filename}}"""
    if HASH_INDEX_PATH.exists():
        return json.loads(HASH_INDEX_PATH.read_text(encoding="utf-8"))
    return {}


def save_hash_index(index: Dict[str, Dict[str, str]]) -> None:
    HASH_INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def scan_duplicates() -> List[Dict]:
    """Scan for duplicate files across dedup namespaces.

    Returns list of {namespace, files: [{path, hash, size, is_original}]}
    """
    results = []
    for ns in sorted(DEDUP_NAMESPACES):
        files = sorted(DATA_PATH.glob(f"{ns}.*.json"))
        if not files:
            continue

        seen_hashes: Dict[str, Path] = {}
        group = {"namespace": ns, "files": [], "dupes": 0, "saved_bytes": 0}

        for f in files:
            file_hash = sha256_file(f)
            size = f.stat().st_size
            is_original = file_hash not in seen_hashes
            if is_original:
                seen_hashes[file_hash] = f
            else:
                group["dupes"] += 1
                group["saved_bytes"] += size

            group["files"].append({
                "path": str(f),
                "hash": file_hash,
                "size": size,
                "is_original": is_original,
                "original": str(seen_hashes[file_hash]) if not is_original else None,
            })

        results.append(group)
    return results


def apply_dedup(dry_run: bool = True) -> Dict[str, int]:
    """Apply deduplication: replace duplicate files with symlinks or remove them.

    For Git repos, we remove duplicates and record the mapping in hash-index.json.
    The manifest generator can reference source_file for deduped entries.
    """
    index = load_hash_index()
    stats = {"scanned": 0, "dupes": 0, "removed": 0, "saved_bytes": 0}

    for ns in sorted(DEDUP_NAMESPACES):
        files = sorted(DATA_PATH.glob(f"{ns}.*.json"))
        if not files:
            continue

        ns_index = index.get(ns, {})
        seen_hashes: Dict[str, Path] = {}

        for f in files:
            stats["scanned"] += 1
            file_hash = sha256_file(f)
            size = f.stat().st_size

            if file_hash in seen_hashes:
                # Duplicate of an earlier file in the same namespace
                stats["dupes"] += 1
                stats["saved_bytes"] += size
                if not dry_run:
                    f.unlink()
                    stats["removed"] += 1
                    print(f"  removed: {f.name} (dup of {seen_hashes[file_hash].name})")
                else:
                    print(f"  would remove: {f.name} (dup of {seen_hashes[file_hash].name}, {size/1024:.0f}KB)")
            else:
                seen_hashes[file_hash] = f
                ns_index[file_hash] = f.name

        index[ns] = ns_index

    if not dry_run:
        save_hash_index(index)
        print(f"\nHash index saved to {HASH_INDEX_PATH}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Raw file deduplication")
    parser.add_argument("--apply", action="store_true", help="Apply dedup (remove duplicates)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    args = parser.parse_args()

    if args.stats:
        results = scan_duplicates()
        total_dupes = 0
        total_saved = 0
        for g in results:
            print(f"{g['namespace']}: {len(g['files'])} files, {g['dupes']} dupes, {g['saved_bytes']/1024/1024:.1f}MB potential savings")
            total_dupes += g["dupes"]
            total_saved += g["saved_bytes"]
        print(f"\nTotal: {total_dupes} duplicates, {total_saved/1024/1024:.1f}MB potential savings")
        return

    dry_run = not args.apply
    print(f"{'DRY RUN' if dry_run else 'APPLYING'} deduplication...\n")
    stats = apply_dedup(dry_run=dry_run)

    print(f"\n{'='*50}")
    print(f"Scanned: {stats['scanned']} files")
    print(f"Duplicates found: {stats['dupes']}")
    print(f"{'Would remove' if dry_run else 'Removed'}: {stats['removed'] if not dry_run else stats['dupes']} files")
    print(f"Space saved: {stats['saved_bytes']/1024/1024:.1f}MB")


if __name__ == "__main__":
    main()
