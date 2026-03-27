"""
KPL 数据采集配置

在此配置需要采集的 API 接口
"""

# 数据源基础 URL
BASE_URL = "https://kpl.qq.com"

# API 接口配置列表
# 格式：{命名空间，接口路径，是否启用}
APIS = [
    # 战队数据
    {"namespace": "team", "path": "/api/team/stats", "enabled": True},
    
    # 选手数据
    {"namespace": "player", "path": "/api/player/stats", "enabled": True},
    
    # 比赛列表
    {"namespace": "match", "path": "/api/match/list", "enabled": True},
    
    # 英雄池
    {"namespace": "hero", "path": "/api/hero/list", "enabled": True},
    
    # 示例：禁用某个接口
    # {"namespace": "example", "path": "/api/example", "enabled": False},
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
