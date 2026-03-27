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

    def save(self, filename: str, data: Any) -> str:
        """
        保存数据到文件

        Args:
            filename: 文件名（不含扩展名）
            data: 数据

        Returns:
            保存的文件路径
        """
        filepath = os.path.join(self.data_dir, f"{filename}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[INFO] 已保存：{filepath}")
        return filepath
