"""
KPL 数据采集配置

在此配置需要采集的 API 接口
"""

# 当前赛季 ID（需要定期更新）
CURRENT_SEASON = "KPL2026S1"

# API 接口配置列表
# 格式：{命名空间，完整 URL，是否启用}
# 注意：URL 中的赛季 ID 需要手动更新，或使用 CURRENT_SEASON 变量
APIS = [
    # === 赛季基础数据 ===
    # 赛季列表（低频，3 个月左右更新一次）
    {"namespace": "seasons-list", "url": "http://47.102.210.150:5006/seasons/list", "enabled": True},
    
    # 当前赛季信息（低频，固定不更新）
    {"namespace": f"season.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5006/season/{CURRENT_SEASON}", "enabled": True},
    
    # === 选手数据（赛季期间每日更新） ===
    # 选手统计数据
    {"namespace": f"player-stats.{CURRENT_SEASON}", "url": f"http://47.103.107.144/openapi/player_stats?seasonid={CURRENT_SEASON}", "enabled": True},
    
    # 所有选手数据
    {"namespace": f"all-player-stats.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5035/api/all-player-stats?season={CURRENT_SEASON}", "enabled": True},
    
    # 选手英雄胜场统计
    {"namespace": f"player-hero-summary.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5028/api/player-hero-summary/{CURRENT_SEASON}", "enabled": True},
    
    # 选手能力数据
    {"namespace": f"player-abilities.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5035/api/player-abilities/{CURRENT_SEASON}", "enabled": True},
    
    # 选手获胜统计
    {"namespace": f"player-win-stats.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5028/api/player-win-stats/{CURRENT_SEASON}", "enabled": True},
    
    # 选手失败统计
    {"namespace": f"player-lose-stats.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5028/api/player-lose-stats/{CURRENT_SEASON}", "enabled": True},
    
    # === 战队数据 ===
    # 战队人员信息（低频，固定不更新）
    {"namespace": f"team-members.{CURRENT_SEASON}.KSG", "url": f"http://47.102.210.150:5006/{CURRENT_SEASON}/KSG", "enabled": True},
    
    # 战队选手伤害分布
    {"namespace": f"team-damage.{CURRENT_SEASON}.KSG", "url": f"http://47.102.210.150:5035/api/team-damage-distribution/{CURRENT_SEASON}/KSG", "enabled": True},
    
    # === 无言选手职业生涯（每日更新） ===
    {"namespace": "ksg.wuyan", "url": "http://47.102.210.150:5049/api/player-career?player_name=KSG.%E6%97%A0%E8%A8%80", "enabled": True},
    
    # === 赛事数据（赛季期间每日更新） ===
    # 赛事回顾
    {"namespace": f"records.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5022/api/records?season={CURRENT_SEASON}", "enabled": True},
    
    # 获胜时选手亲近度分析
    {"namespace": f"win-affinity.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5029/api/{CURRENT_SEASON}/win-affinity-analysis", "enabled": True},
    
    # === 英雄数据 ===
    # 联盟英雄胜率（对抗路）
    {"namespace": f"hero-win-rate.{CURRENT_SEASON}", "url": f"http://47.102.210.150:5035/api/hero-win-rate/{CURRENT_SEASON}?position=%E5%AF%B9%E6%8A%97%E8%B7%AF", "enabled": True},
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
