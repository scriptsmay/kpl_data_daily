"""
KPL 数据存储器
"""

import json
import os
from datetime import datetime
from typing import Any, Optional

from .config import DATA_DIR, DATE_FORMAT


class KPLStorage:
    """KPL 数据存储器"""

    def __init__(self, data_dir: Optional[str] = None):
        """初始化存储器"""
        self.data_dir = data_dir or DATA_DIR
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save(self, namespace: str, data: Any, date: Optional[datetime] = None) -> str:
        """
        保存数据到文件

        文件名格式：{namespace}_{date}.json

        Args:
            namespace: 命名空间
            data: 数据
            date: 日期，默认今天

        Returns:
            保存的文件路径
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime(DATE_FORMAT)
        filename = f"{namespace}_{date_str}.json"
        filepath = os.path.join(self.data_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[INFO] 已保存：{filepath}")
        return filepath
