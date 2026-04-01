"""
KPL 数据采集器
"""

import json
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import HEADERS, MAX_RETRIES, REQUEST_TIMEOUT, RETRY_DELAY, REQUEST_DELAY


class KPLCrawler:
    """KPL 数据采集器"""

    def __init__(self):
        """初始化采集器"""
        self.session = self._create_session()
        self.last_request_time = 0

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

    def _wait_for_delay(self, delay: float = None):
        """等待请求间隔"""
        if delay is None:
            delay = REQUEST_DELAY
        
        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def fetch(self, url: str, params: Optional[dict] = None, timeout: int = None, delay: float = None) -> Optional[Any]:
        """
        获取 API 数据

        Args:
            url: 完整 URL
            params: 查询参数
            timeout: 超时时间（秒），默认为配置中的值
            delay: 请求间隔（秒），默认为配置中的值

        Returns:
            响应数据
        """
        if timeout is None:
            timeout = REQUEST_TIMEOUT
        
        self._wait_for_delay(delay)

        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 请求失败 {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 解析失败 {url}: {e}")
            return None
