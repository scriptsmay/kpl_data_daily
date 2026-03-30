# KPL Data Daily

github: https://github.com/scriptsmay/kpl_data_daily

KPL 数据采集工具，每日定时抓取 API 数据，自动筛选关注的选手（无言）数据。

## 功能

- 📊 **配置化采集**：在配置文件中定义 API 接口
- 🎯 **选手筛选**：自动从批量数据中筛选指定选手的数据
- ⏰ **智能判断**：根据赛季日期自动判断是否执行采集
- 💾 **历史积累**：保留所有历史数据，用于未来 AI 分析
- 🔄 **自动同步**：GitHub Actions 自动提交数据到仓库

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行

```bash
python main.py
```

数据保存在 `data/` 目录。

## GitHub Actions

每天 UTC 00:00（北京时间 08:00）自动执行。

## 配置说明

### src/crawler/config.py

```python
# 关注的选手
TARGET_PLAYER = "KSG.无言"

# 战队名称
TARGET_TEAM = "KSG"

# API 接口配置
APIS = [
    {
        "namespace": "player-stats",
        "url": "http://47.103.107.144/openapi/player_stats?seasonid={season_id}",
        "update_freq": "daily",  # daily 或 fixed
        "need_filter": True,    # 是否需要筛选选手数据
    },
]
```

## 输出文件

### 固定数据（只采集一次）

- `seasons-list.{赛季 ID}.json` - 赛季列表
- `season.{赛季 ID}.json` - 赛季信息
- `team-members.{赛季 ID}.json` - 战队人员

### 每日数据（每天采集，保留历史）

- `player-stats.{赛季 ID}.{日期}.json` - 无言选手统计
- `all-player-stats.{赛季 ID}.{日期}.json` - 无言选手全部数据
- `player-hero-summary.{赛季 ID}.{日期}.json` - 无言英雄胜场
- `player-abilities.{赛季 ID}.{日期}.json` - 无言能力数据
- `player-win-stats.{赛季 ID}.{日期}.json` - 无言获胜统计
- `player-lose-stats.{赛季 ID}.{日期}.json` - 无言失败统计
- `player-career-wuyan.{赛季 ID}.{日期}.json` - 无言职业生涯
- `season-records.{赛季 ID}.{日期}.json` - 赛事回顾
- `win-affinity-analysis.{赛季 ID}.{日期}.json` - 获胜亲近度
- `team-damage-distribution.{赛季 ID}.{日期}.json` - KSG 伤害分布
- `hero-win-rate.{赛季 ID}.{日期}.json` - 英雄胜率（对抗路）

所有数据文件都会提交到 Git 仓库，长期积累用于后续 AI 分析。

## 采集流程

1. 获取赛季列表，找到 `project=KPL` 且 `is_latest=1` 的赛季
2. 检查赛季是否在有效期内（开始日期 ~ 结束日期 +1 天）
3. 如果不在有效期内，跳过采集
4. 替换 URL 中的 `{season_id}` 和 `{team_name}` 参数
5. 采集数据并保存
