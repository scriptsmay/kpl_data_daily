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

### 方式一：uv（推荐）

```bash
# 安装 uv（如尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 一键运行（自动创建虚拟环境、安装依赖）
uv run main.py

# 只跑后处理（不重新抓取，用于测试 AI insights）
uv run post_process.py
```

首次运行时 uv 会自动读取 `pyproject.toml`，创建 `.venv` 并安装依赖，无需手动操作。

如需手动管理依赖：

```bash
# 同步依赖
uv sync

# 添加新依赖
uv add <package>
```

### 方式二：pip

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 环境变量配置

创建 `.env` 文件（已在 `.gitignore` 中，不会提交）：

```bash
OPENAI_API_KEY=sk-你的key          # 必填，AI 分析功能
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，默认 OpenAI
OPENAI_MODEL=gpt-4o-mini           # 可选，默认 gpt-4o-mini
```

`main.py` 启动时会自动加载 `.env`。不配置时，AI 分析会被跳过，不影响数据采集。

## GitHub Actions

每天 UTC 00:00（北京时间 08:00）自动执行。

## 配置说明

### src/crawler/config.py

```python
# 关注的选手
TARGET_PLAYER = "无言"

# 战队名称
TARGET_TEAM = "KSG"

# API 接口配置
APIS = [
    {
        "namespace": "player-stats",
        "url": "http://47.103.107.144/openapi/player_stats?season_id={season_id}",
        "update_freq": "daily",  # daily 或 fixed
        "need_filter": True,    # 是否需要筛选选手数据
    },
    {
        "namespace": "seasons-list",
        "url": "http://47.102.210.150:5006/seasons/list?project=KPL",
        "update_freq": "fixed",
        "no_season": True,      # 文件名不带赛季 ID
        "overwrite": True,      # 文件已存在时覆盖保存
    },
]
```

### 配置项说明

| 配置项        | 类型    | 说明                                                 |
| ------------- | ------- | ---------------------------------------------------- |
| `namespace`   | string  | 命名空间，用于生成输出文件名                         |
| `url`         | string  | API 地址，支持 `{season_id}` 和 `{team_name}` 占位符 |
| `update_freq` | string  | 更新频率：`fixed`（固定）或 `daily`（每日）          |
| `need_filter` | boolean | 是否需要从批量数据中筛选选手                         |
| `no_season`   | boolean | 文件名中省略赛季 ID（默认 `False`）                  |
| `enabled`     | boolean | 是否启用该 API                                       |
| `overwrite`   | boolean | 文件已存在时是否覆盖保存（默认 `False`）             |

## 输出文件

### 固定数据（只采集一次）

- `seasons-list.json` - 赛季列表（无赛季 ID，每日覆盖更新）
- `season.{赛季 ID}.json` - 赛季信息
- `team-members.{赛季 ID}.json` - 战队人员

### 每日数据（每天采集，保留历史）

- `player-stats.{赛季 ID}.{日期}.json` - 无言选手统计
- `all-player-stats.{赛季 ID}.{日期}.json` - 无言选手全部数据
- `player-hero-summary.{赛季 ID}.{日期}.json` - 无言英雄胜场
- `player-abilities.{赛季 ID}.{日期}.json` - 无言能力数据
- `player-win-stats.{赛季 ID}.{日期}.json` - 无言获胜统计
- `player-lose-stats.{赛季 ID}.{日期}.json` - 无言失败统计
- `player-career-wuyan.{日期}.json` - 无言职业生涯（无赛季 ID）
- `season-records.{赛季 ID}.{日期}.json` - 赛事回顾
- `win-affinity-analysis.{赛季 ID}.{日期}.json` - 获胜亲近度
- `team-damage-distribution.{赛季 ID}.{日期}.json` - KSG 伤害分布
- `hero-win-rate.{赛季 ID}.{日期}.json` - 英雄胜率（对抗路）
- `player-hero-battles.{赛季 ID}.{日期}.json` - 英雄对局详情（出装/铭文/阵容/KDA）

### 文件名说明

| 类型      | 格式                                      | 示例                                   |
| --------- | ----------------------------------------- | -------------------------------------- |
| 普通文件  | `{namespace}.{season_id}.json`            | `season.KPL2026S1.json`                |
| 每日数据  | `{namespace}.{season_id}.{YYYYMMDD}.json` | `player-stats.KPL2026S1.20260330.json` |
| 无赛季 ID | `{namespace}.json`                        | `seasons-list.json`                    |

所有数据文件都会提交到 Git 仓库，长期积累用于后续 AI 分析。

## 发布数据视图

每日抓取完成后会运行 `post_process.py`，生成面向前端和 AI 的稳定读取入口。

### manifest

- `data/manifest.json` - 全量数据文件索引，包含 namespace、season、date、文件路径、SHA-256、大小和更新时间。

### latest

- `data/latest/current-season.json` - 当前赛季唯一权威入口，包含 `schema_version`、`current`、`season_name`、`updated_at`、`build_id`。
- `data/latest/seasons-list.json` - 最新赛季列表。
- `data/latest/{season}/{namespace}.json` - 当前赛季各模块最新数据，文件名去掉日期后缀并覆盖更新。

### derived

- `data/derived/{season}/overview.json` - 职业概览、赛季摘要、近期比赛。
- `data/derived/{season}/abilities.json` - 能力画像页数据。
- `data/derived/{season}/ranking.json` - 联盟排名页数据。
- `data/derived/{season}/heroes.json` - 英雄池页聚合数据。
- `data/derived/{season}/win-lose.json` - 胜负对比页数据。
- `data/derived/{season}/insights.json` - 规则生成的轻量洞察，后续可接入 AI 生成文案。

所有 derived 文件均包含 `schema_version`、`season`、`generated_at`、`build_id`，消费端必须用这些字段校验数据版本和发布批次。

## 请求配置

### 请求间隔

为了避免接口请求过于频繁，配置了请求间隔：

| 配置项                | 默认值 | 说明                                     |
| --------------------- | ------ | ---------------------------------------- |
| `REQUEST_DELAY`       | 1.0s   | 普通接口之间的请求间隔                   |
| `REQUEST_DELAY_LARGE` | 3.0s   | 大数据量接口（如英雄对局详情）的请求间隔 |

### 超时时间

| 配置项             | 默认值 | 说明                         |
| ------------------ | ------ | ---------------------------- |
| `REQUEST_TIMEOUT`  | 30s    | 默认请求超时时间             |
| 大数据量接口       | 60s    | 英雄对局详情等大数据量接口   |

## 错误处理

- **容错机制**：单个接口请求失败不会中断整个流程，会继续执行后续接口
- **重试机制**：使用 urllib3 的 Retry，遇到 429/500/502/503/504 会自动重试
- **GitHub Actions**：使用 `continue-on-error` 确保即使部分失败也能提交已成功采集的数据

## 采集流程

### 一级抓取：基础数据

1. 获取赛季列表，找到 `project=KPL` 且 `is_latest=1` 的赛季
2. 检查赛季是否在有效期内（开始日期 ~ 结束日期 +3 天）
3. 如果不在有效期内，跳过采集
4. 从职业生涯数据中读取选手名称和战队名称
5. 替换 URL 中的 `{season_id}` 和 `{team_name}` 参数
6. 采集数据并保存（支持容错，单个接口失败不影响其他接口）

### 二级抓取：英雄对局详情

在一级抓取完成后，执行二级抓取：

1. 从 `player-hero-summary` 文件中提取本赛季使用的所有英雄
2. 遍历英雄列表，获取每个英雄的详细对局数据
3. 统计胜率、出装、铭文、阵容等信息
4. 保存至 `player-hero-battles.{赛季 ID}.{日期}.json`

详细流程请参考 [doc/guide.md](doc/guide.md)。
