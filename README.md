# KPL Data Daily

KPL 数据采集工具，每日定时抓取 API 数据并保存为 JSON 文件。

## 功能

- 📊 **配置化采集**：在配置文件中定义 API 接口（支持多域名）
- ⏰ **定时执行**：GitHub Actions 每日自动运行
- 💾 **JSON 存储**：按 `{命名空间}.json` 格式保存

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置接口

编辑 `src/crawler/config.py`：

```python
# 当前赛季 ID
CURRENT_SEASON = "KPL2026S1"

# API 接口配置
APIS = [
    {"namespace": "player-stats", "url": "http://47.103.107.144/openapi/player_stats?seasonid=KPL2026S1", "enabled": True},
    # ... 更多接口
]
```

### 3. 运行

```bash
python main.py
```

数据保存在 `data/` 目录：
```
data/
├── player-stats.KPL2026S1.json
├── ksg.wuyan.json
└── ...
```

## GitHub Actions

项目已配置 GitHub Actions，每天 UTC 00:00（北京时间 08:00）自动执行。

## 已配置的 API

| 命名空间 | 描述 | 更新频率 |
|----------|------|----------|
| `seasons-list` | 赛季列表 | 低频 |
| `season.{赛季}` | 赛季信息 | 固定 |
| `player-stats.{赛季}` | 选手统计 | 每日 |
| `all-player-stats.{赛季}` | 所有选手数据 | 每日 |
| `player-hero-summary.{赛季}` | 选手英雄胜场 | 每日 |
| `player-abilities.{赛季}` | 选手能力数据 | 每日 |
| `player-win-stats.{赛季}` | 选手获胜统计 | 每日 |
| `player-lose-stats.{赛季}` | 选手失败统计 | 每日 |
| `team-members.{赛季}.{战队}` | 战队人员 | 固定 |
| `team-damage.{赛季}.{战队}` | 战队伤害分布 | 每日 |
| `ksg.wuyan` | 无言职业生涯 | 每日 |
| `records.{赛季}` | 赛事回顾 | 每日 |
| `win-affinity.{赛季}` | 获胜亲近度 | 每日 |
| `hero-win-rate.{赛季}` | 英雄胜率 | 每日 |

## 更新赛季

当新赛季开始时，编辑 `src/crawler/config.py`：

```python
CURRENT_SEASON = "新赛季 ID"  # 例如：KPL2026S2
```
