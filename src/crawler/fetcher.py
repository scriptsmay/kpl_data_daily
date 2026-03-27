"""
KPL 数据采集器
"""

import json
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import HEADERS, MAX_RETRIES, REQUEST_TIMEOUT, RETRY_DELAY


class KPLCrawler:
    """KPL 数据采集器"""

    def __init__(self):
        """初始化采集器"""
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建带重试机制的 Session"""
        session = requests.Session()
        session.headers.update(HEADERS)

        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def fetch(self, url: str, params: Optional[dict] = None) -> Optional[Any]:
        """
        获取 API 数据

        Args:
            url: 完整 URL
            params: 查询参数

        Returns:
            响应数据
        """
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            time.sleep(0.5)  # 避免请求过快
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 请求失败 {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 解析失败 {url}: {e}")
            return None
