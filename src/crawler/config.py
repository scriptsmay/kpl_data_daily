"""
KPL 数据采集配置

在此配置需要采集的 API 接口
"""

# API 接口配置列表
# 格式：{命名空间，完整 URL，是否启用}
APIS = [
    # 示例配置 - 请替换为真实的 API 地址
    # {"namespace": "team", "url": "https://api.example.com/team/stats", "enabled": True},
    # {"namespace": "player", "url": "https://api.example.com/player/stats", "enabled": True},
    # {"namespace": "match", "url": "https://kpl.qq.com/api/match/list", "enabled": True},
    # {"namespace": "hero", "url": "https://kpl.qq.com/api/hero/list", "enabled": True},
    {"namespace": "team", "url": "http://47.102.210.150:5006/KPL2026S1/KSG", "enabled": True}
]

# 请求配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

REQUEST_TIMEOUT = 30  # 秒
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 1  # 重试间隔（秒）

# 输出配置
DATA_DIR = "data"  # 数据保存目录
DATE_FORMAT = "%Y%m%d"  # 日期格式
