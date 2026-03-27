#!/usr/bin/env python3
"""
KPL 数据采集工具

每日定时抓取配置中的 API 接口数据
保存格式：data/{命名空间}_{日期}.json
"""

import sys

from src.crawler.config import APIS
from src.crawler.fetcher import KPLCrawler
from src.storage.saver import KPLStorage


def run() -> int:
    """执行数据采集"""
    print("=" * 50)
    print("KPL 数据采集开始")
    print("=" * 50)

    crawler = KPLCrawler()
    storage = KPLStorage()

    success_count = 0
    fail_count = 0

    for api in APIS:
        if not api.get("enabled", True):
            print(f"[SKIP] {api['namespace']} (已禁用)")
            continue

        namespace = api["namespace"]
        path = api["path"]

        print(f"\n[FETCH] {namespace}: {path}")

        data = crawler.fetch(path)

        if data is not None:
            storage.save(namespace, data)
            success_count += 1
        else:
            print(f"[FAIL] {namespace} 采集失败")
            fail_count += 1

    print("\n" + "=" * 50)
    print(f"采集完成：成功 {success_count} 个，失败 {fail_count} 个")
    print("=" * 50)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
