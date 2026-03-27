"""
KPL 数据采集配置
"""

from datetime import datetime
from typing import List, Dict

# 当前赛季 ID（自动获取，此处为默认值）
CURRENT_SEASON = "KPL2026S1"

# 关注的选手
TARGET_PLAYER = "KSG.无言"

# 战队名称
TARGET_TEAM = "KSG"

# API 接口配置
# update_freq: "fixed" (固定/不更新) 或 "daily" (每日更新)
# need_filter: 是否需要从批量数据中筛选目标选手
APIS: List[Dict] = [
    # === 固定频率 API（只抓取一次） ===
    {
        "namespace": "seasons-list",
        "url": "http://47.102.210.150:5006/seasons/list",
        "update_freq": "fixed",
        "enabled": True,
    },
    {
        "namespace": "season",
        "url": "http://47.102.210.150:5006/season/{season_id}",
        "update_freq": "fixed",
        "enabled": True,
    },
    {
        "namespace": "team-members",
        "url": "http://47.102.210.150:5006/{season_id}/{team_name}",
        "update_freq": "fixed",
        "enabled": True,
    },
    
    # === 每日更新 API ===
    {
        "namespace": "player-stats",
        "url": "http://47.103.107.144/openapi/player_stats?seasonid={season_id}",
        "update_freq": "daily",
        "need_filter": True,  # 需要筛选无言的数据
        "enabled": True,
    },
    {
        "namespace": "all-player-stats",
        "url": "http://47.102.210.150:5035/api/all-player-stats?season={season_id}",
        "update_freq": "daily",
        "need_filter": True,
        "enabled": True,
    },
    {
        "namespace": "player-hero-summary",
        "url": "http://47.102.210.150:5028/api/player-hero-summary/{season_id}",
        "update_freq": "daily",
        "need_filter": True,
        "enabled": True,
    },
    {
        "namespace": "player-abilities",
        "url": "http://47.102.210.150:5035/api/player-abilities/{season_id}",
        "update_freq": "daily",
        "need_filter": True,
        "enabled": True,
    },
    {
        "namespace": "player-win-stats",
        "url": "http://47.102.210.150:5028/api/player-win-stats/{season_id}",
        "update_freq": "daily",
        "need_filter": True,
        "enabled": True,
    },
    {
        "namespace": "player-lose-stats",
        "url": "http://47.102.210.150:5028/api/player-lose-stats/{season_id}",
        "update_freq": "daily",
        "need_filter": True,
        "enabled": True,
    },
    {
        "namespace": "player-career-wuyan",
        "url": "http://47.102.210.150:5049/api/player-career?player_name=KSG.%E6%97%A0%E8%A8%80",
        "update_freq": "daily",
        "enabled": True,
    },
    {
        "namespace": "season-records",
        "url": "http://47.102.210.150:5022/api/records?season={season_id}",
        "update_freq": "daily",
        "enabled": True,
    },
    {
        "namespace": "win-affinity-analysis",
        "url": "http://47.102.210.150:5029/api/{season_id}/win-affinity-analysis",
        "update_freq": "daily",
        "enabled": True,
    },
    {
        "namespace": "team-damage-distribution",
        "url": "http://47.102.210.150:5035/api/team-damage-distribution/{season_id}/{team_name}",
        "update_freq": "daily",
        "enabled": True,
    },
    {
        "namespace": "hero-win-rate",
        "url": "http://47.102.210.150:5035/api/hero-win-rate/{season_id}?position=%E5%AF%B9%E6%8A%97%E8%B7%AF",
        "update_freq": "daily",
        "enabled": True,
    },
]

# 请求配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1

# 输出配置
DATA_DIR = "data"
DATE_FORMAT = "%Y%m%d"
