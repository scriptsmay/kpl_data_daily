# KPL Data Daily - 项目上下文

## 项目概述

**KPL Data Daily** 是一个 KPL 数据采集工具，通过 GitHub Actions 每日定时抓取 API 数据。

### 核心功能

1. **配置化采集** - 在 `config.py` 中定义 API 接口列表
2. **定时执行** - GitHub Actions 每天自动运行
3. **JSON 存储** - 按 `{命名空间}.json` 格式保存

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
│   ├── archive/               # 历史数据归档
│   └── *.json                 # 采集的数据
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
# 当前赛季 ID（需要定期更新）
CURRENT_SEASON = "KPL2026S1"

# API 接口配置（支持多域名）
APIS = [
    {"namespace": "player-stats", "url": "http://47.103.107.144/openapi/player_stats?seasonid=KPL2026S1", "enabled": True},
]
```

### 输出格式

文件保存在 `data/` 目录，命名格式：`{namespace}.json`

示例：
- `player-stats.KPL2026S1.json`
- `ksg.wuyan.json`
- `team-members.KPL2026S1.KSG.json`

## 已配置的 API

参考 `doc/API.md` 了解所有 API 详情。

## 更新赛季

当新赛季开始时，修改 `src/crawler/config.py` 中的 `CURRENT_SEASON` 变量。
