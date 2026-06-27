# KPL Data Daily - 项目上下文

## 项目概述

**KPL Data Daily** 是 KPL（王者荣耀职业联赛）数据采集与分析工具。每日定时抓取 API 数据，自动筛选"无言"（KSG.无言，对抗路）选手的数据，并通过后处理模块生成结构化洞察和 AI 分析报告。

### 核心功能

1. **配置化采集** - 在 `src/crawler/config.py` 中定义 API 接口列表
2. **智能判断** - 根据赛季日期自动判断是否执行采集
3. **选手筛选** - 从批量数据中筛选指定选手（无言）的数据
4. **后处理与洞察** - `post_process.py` 生成 latest 快照、derived 分析、规则洞察
5. **AI 分析** - 调用 LLM（OpenAI 兼容接口）生成中文赛事洞察 + Markdown 日报
6. **历史赛季支持** - `-s` 参数可对历史赛季重新生成 derived 数据
7. **自动同步** - GitHub Actions 每日自动执行并提交数据

### 技术栈

- **语言**: Python 3.11+
- **包管理**: uv（推荐）/ pip
- **依赖**: requests, openai, python-dotenv
- **AI 接口**: OpenAI 兼容 API（默认 qwen3.7-max，可配置）
- **自动化**: GitHub Actions

## 项目结构

```
kpl_data_daily/
├── main.py                         # 主程序入口：数据采集
├── post_process.py                 # 后处理入口：latest / derived / AI insights
├── pyproject.toml                  # uv 项目配置 & 依赖声明
├── uv.lock                         # uv 锁文件
├── requirements.txt                # pip 依赖（兼容）
├── .env.example                    # 环境变量示例
├── .github/workflows/
│   └── daily-fetch.yml             # GitHub Actions 配置
├── data/                           # 数据目录
│   ├── *.json                      # 原始采集数据
│   ├── latest/                     # 当前赛季最新快照
│   │   ├── current-season.json
│   │   ├── player-career-wuyan.json
│   │   └── {season}/{namespace}.json
│   ├── derived/                    # 当前赛季派生数据
│   │   └── {season}/
│   │       ├── overview.json, abilities.json, heroes.json
│   │       ├── ranking.json, win-lose.json, insights.json
│   │       ├── ai-insights.json, trend-summary.json, growth-path.json
│   │       └── ...
│   └── seasons/                    # 历史赛季数据（-s 模式输出）
│       └── {season}/
│           ├── latest/             # 该赛季的最新快照
│           ├── derived/            # 该赛季的派生数据 + AI insights
│           └── manifest.json
├── reports/
│   └── daily/{YYYY-MM-DD}.md       # AI 生成的 Markdown 日报
├── doc/
│   ├── API.md                      # API 详细说明
│   ├── guide.md                    # 抓取流程说明
│   └── params_explain.md           # 数据标注文档
└── src/
    ├── crawler/
    │   ├── config.py               # API 接口配置 & 采集参数
    │   └── fetcher.py              # 数据采集器
    ├── storage/
    │   ├── config.py               # 项目路径配置（DATA_DIR 等）
    │   └── saver.py                # 数据存储器
    └── analysis/
        ├── metrics.py              # 核心指标计算（英雄池、能力、排名、胜负差）
        ├── trends.py               # 多快照趋势分析
        ├── growth_path.py          # 成长路径生成
        ├── hero_maturity.py        # 英雄成熟度分类
        ├── prompts.py              # AI prompt 构建（系统提示 + 数据格式化）
        └── ai_insights.py          # AI 洞察生成 + 日报输出
```

## 运行方式

### 本地运行（uv 推荐）

```bash
# 数据采集（自动判断赛季、抓取 API）
uv run main.py

# 后处理：当前赛季（生成 latest / derived / AI insights）
uv run post_process.py

# 后处理：指定历史赛季
uv run post_process.py -s KPL2026S1

# 列出所有可用赛季
uv run post_process.py --list-seasons
```

### pip 方式

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
python post_process.py -s KPL2026S1
```

### 环境变量

创建 `.env` 文件（已在 `.gitignore` 中，不会提交）：

```bash
OPENAI_API_KEY=sk-你的key          # AI 分析功能（不配置则跳过 AI）
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，默认 OpenAI
OPENAI_MODEL=gpt-4o-mini           # 可选，默认 gpt-4o-mini
```

### 定时执行

GitHub Actions 每天 UTC 01:16（北京时间 09:16）自动执行。

## 数据处理流程

### 采集阶段（main.py）

1. 获取赛季列表，找到 `project="KPL"` 且 `is_latest=1` 的赛季
2. 检查是否在有效采集期内（开始日期 ~ 结束日期 +1 天）
3. 替换 URL 中的 `{season_id}` 和 `{team_name}`
4. 采集数据，筛选选手数据，保存原始 JSON 文件
5. 执行二级采集：英雄对局详情

### 后处理阶段（post_process.py）

1. **生成 latest 快照** — 每个命名空间取最新日期的文件
2. **生成 derived 派生数据**：
   - `overview.json` — 选手生涯概览（来自 player-career-wuyan）
   - `abilities.json` — 能力画像（来自 player-abilities）
   - `ranking.json` — 联盟排名（来自 all-player-stats）
   - `heroes.json` — 英雄汇总（合并 hero-summary + battles + win-rate）
   - `win-lose.json` — 胜负差异（来自 player-win/lose-stats）
   - `trend-summary.json` — 多快照趋势分析
   - `growth-path.json` — 成长路径
   - `insights.json` — 规则洞察（基于 metrics 的结构化分析）
3. **生成 AI 洞察**（可选）：
   - 调用 LLM API 生成 `ai-insights.json`
   - 同时生成 `reports/daily/{YYYY-MM-DD}.md` 日报
4. **生成 manifest** — 索引所有输出文件的 hash、大小、时间

## 配置说明

### src/crawler/config.py

| 配置项        | 类型    | 说明                                                       |
| ------------- | ------- | ---------------------------------------------------------- |
| `namespace`   | string  | 命名空间，用于生成输出文件名                               |
| `url`         | string  | API 地址，支持 `{season_id}` 和 `{team_name}` 占位符       |
| `update_freq` | string  | 更新频率：`fixed`（固定/只采集一次）或 `daily`（每日更新） |
| `need_filter` | boolean | 是否需要从批量数据中筛选目标选手                           |
| `no_season`   | boolean | 是否在文件名中省略赛季 ID（默认为 `False`）                |
| `enabled`     | boolean | 是否启用该 API 采集                                        |

## 输出文件命名

- **固定数据**: `{namespace}.{赛季ID}.json`
- **每日数据**: `{namespace}.{赛季ID}.{YYYYMMDD}.json`
- **无赛季 ID**: `{namespace}.{YYYYMMDD}.json`（如 `player-career-wuyan.20260627.json`）

## 参考文档

- `doc/API.md` - API 详细说明
- `doc/guide.md` - 抓取流程说明
- `doc/params_explain.md` - 数据标注文档
