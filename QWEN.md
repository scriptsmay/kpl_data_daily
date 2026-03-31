# KPL Data Daily - 项目上下文

## 项目概述

**KPL Data Daily** 是一个 KPL 数据采集工具，每日定时抓取 API 数据，自动筛选"无言"选手的数据。

### 核心功能

1. **配置化采集** - 在 `config.py` 中定义 API 接口列表
2. **智能判断** - 根据赛季日期自动判断是否执行采集
3. **选手筛选** - 从批量数据中筛选指定选手（无言）的数据
4. **历史积累** - 保留所有历史数据，用于未来 AI 分析
5. **自动同步** - GitHub Actions 自动提交数据到仓库

### 技术栈

- **语言**: Python 3.8+
- **依赖**: requests
- **自动化**: GitHub Actions

## 项目结构

```
kpl_data_daily/
├── main.py                    # 主程序入口
├── requirements.txt           # 项目依赖
├── .github/workflows/
│   └── daily-fetch.yml        # GitHub Actions 配置
├── data/                      # 数据输出目录
│   └── *.json                 # 采集的数据
├── doc/
│   ├── API.md                 # API 详细说明
│   |── guide.md               # 抓取流程说明
|   └── params_explain.md      # 数据标注文档
└── src/
    ├── crawler/
    │   ├── config.py          # API 接口配置
    │   └── fetcher.py         # 数据采集器
    └── storage/
        └── saver.py           # 数据存储器
```

## 运行方式

### 本地运行

```bash
pip install -r requirements.txt
python main.py
```

### 定时执行

GitHub Actions 每天 UTC 00:00（北京时间 08:00）自动执行。

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
        "update_freq": "daily",
        "need_filter": True,
    },
    {
        "namespace": "seasons-list",
        "url": "http://47.102.210.150:5006/seasons/list?project=KPL",
        "update_freq": "fixed",
        "no_season": True,  # 不需要赛季 ID，文件名不带赛季 ID
    },
    {
        "namespace": "player-career-wuyan",
        "url": "http://47.102.210.150:5049/api/player-career?player_name=KSG.%E6%97%A0%E8%A8%80",
        "update_freq": "daily",
        "no_season": True,  # 不需要赛季 ID，文件名不带赛季 ID
    },
]
```

### 配置项说明

| 配置项        | 类型    | 说明                                                       |
| ------------- | ------- | ---------------------------------------------------------- |
| `namespace`   | string  | 命名空间，用于生成输出文件名                               |
| `url`         | string  | API 地址，支持 `{season_id}` 和 `{team_name}` 占位符       |
| `update_freq` | string  | 更新频率：`fixed`（固定/只采集一次）或 `daily`（每日更新） |
| `need_filter` | boolean | 是否需要从批量数据中筛选目标选手                           |
| `no_season`   | boolean | 是否在文件名中省略赛季 ID（默认为 `False`）                |
| `enabled`     | boolean | 是否启用该 API 采集                                        |

## 采集流程

1. 获取赛季列表 (`/seasons/list`)
2. 找到 `project="KPL"` 且 `is_latest=1` 的赛季
3. 获取赛季详细信息（包含开始/结束日期）
4. 检查是否在有效期内（开始日期 ~ 结束日期 +1 天）
5. 替换 URL 中的 `{season_id}` 和 `{team_name}`
6. 采集数据，筛选选手数据，保存文件

## 输出格式

- **固定数据**: `{命名空间}.{赛季 ID}.json`（如 `season.KPL2026S1.json`）
- **每日数据**: `{命名空间}.{赛季 ID}.{YYYYMMDD}.json`（如 `player-stats.KPL2026S1.20260330.json`）
- **无赛季 ID 数据**: `{命名空间}.json`（配置 `no_season: True` 的文件，如 `seasons-list.json`）

所有数据文件都会提交到 Git 仓库，长期积累用于后续 AI 分析。

## 参考文档

- `doc/API.md` - API 详细说明
- `doc/guide.md` - 抓取流程说明
