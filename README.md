# KPL Data Daily

KPL 数据采集工具，每日定时抓取 API 数据并保存为 JSON 文件。

## 功能

- 📊 **配置化采集**：在配置文件中定义 API 接口（支持多域名）
- ⏰ **定时执行**：GitHub Actions 每日自动运行
- 💾 **JSON 存储**：按 `{命名空间}_{日期}.json` 格式保存

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置接口

编辑 `src/crawler/config.py`，在 `APIS` 列表中添加要采集的接口：

```python
APIS = [
    {"namespace": "team", "url": "https://api.example.com/team/stats", "enabled": True},
    {"namespace": "player", "url": "https://kpl.qq.com/api/player/stats", "enabled": True},
    {"namespace": "match", "url": "https://another-domain.com/api/match", "enabled": True},
]
```

> 每个接口使用完整的 URL，支持不同域名

### 3. 运行

```bash
python main.py
```

数据保存在 `data/` 目录：
```
data/
├── team_20240327.json
├── player_20240327.json
├── match_20240327.json
└── ...
```

## GitHub Actions

项目已配置 GitHub Actions，每天 UTC 00:00（北京时间 08:00）自动执行：

- 修改 `.github/workflows/daily-fetch.yml` 调整执行时间
- 支持手动触发（Actions → Daily KPL Data Fetch → Run workflow）

## 项目结构

```
kpl_data_daily/
├── main.py                    # 主程序
├── requirements.txt           # 依赖
├── .github/workflows/
│   └── daily-fetch.yml        # GitHub Actions 配置
├── data/                      # 数据输出目录
└── src/
    ├── crawler/
    │   ├── config.py          # 接口配置
    │   └── fetcher.py         # 采集器
    └── storage/
        └── saver.py           # 存储器
```

## 配置说明

### src/crawler/config.py

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `APIS` | 接口配置列表（命名空间 + 完整 URL） | - |
| `REQUEST_TIMEOUT` | 请求超时（秒） | 30 |
| `MAX_RETRIES` | 最大重试次数 | 3 |
| `DATA_DIR` | 数据保存目录 | data |
| `DATE_FORMAT` | 日期格式 | %Y%m%d |

## 输出文件

文件名格式：`{namespace}_{YYYYMMDD}.json`

示例：
- `team_20240327.json` - 战队数据
- `player_20240327.json` - 选手数据
- `match_20240327.json` - 比赛数据
