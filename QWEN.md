# KPL Data Daily - 项目上下文

## 项目概述

**KPL Data Daily** 是一个简单的 KPL 数据采集工具，通过 GitHub Actions 每日定时抓取配置的 API 接口数据。

### 核心功能

1. **配置化采集** - 在 `config.py` 中定义 API 接口列表
2. **定时执行** - GitHub Actions 每天自动运行
3. **JSON 存储** - 按 `{命名空间}_{日期}.json` 格式保存

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

GitHub Actions 每天 UTC 00:00（北京时间 08:00）自动执行，也可手动触发。

## 配置说明

### src/crawler/config.py

```python
# API 接口配置
APIS = [
    {"namespace": "team", "path": "/api/team/stats", "enabled": True},
    {"namespace": "player", "path": "/api/player/stats", "enabled": True},
]

# 请求配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
```

### 输出格式

文件保存在 `data/` 目录，命名格式：`{namespace}_{YYYYMMDD}.json`

示例：
- `team_20240327.json`
- `player_20240327.json`

## 开发规范

- 代码简洁，只做数据采集
- 遵循 PEP 8 规范
- 类型注解（Type Hints）
