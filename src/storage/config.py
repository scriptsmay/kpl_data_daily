"""
KPL 数据存储模块配置
"""

import os

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# 日期格式
DATE_FORMAT = "%Y%m%d"
