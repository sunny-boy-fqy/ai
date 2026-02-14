#!/usr/bin/env python3
"""测试插件搜索功能"""

import sys
import os

# 添加 tools 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from tools.plugin import PluginManager
from tools.constants import CAPABILITY_KEYWORDS

print("=" * 60)
print("测试插件搜索功能")
print("=" * 60)

# 测试用例
test_queries = [
    "",           # 无查询（应该返回所有插件）
    "postgres",   # 数据库关键词
    "mysql",      # 数据库关键词  
    "database",   # 能力类型
    "browser",    # 浏览器关键词
    "web",        # Web关键词
    "search",     # 搜索能力
    "git",        # Git关键词
    "github",     # GitHub关键词
    "memory",     # 记忆能力
    "slack",      # 通信关键词
    "shell",      # 命令关键词
]

print("\n能力关键词映射 (CAPABILITY_KEYWORDS):")
for cap, keywords in CAPABILITY_KEYWORDS.items():
    print(f"  {cap}: {keywords}")

print("\n" + "=" * 60)
for query in test_queries:
    print(f"\n搜索查询: '{query}'")
    print("-" * 40)
    results = PluginManager.search(query)
    if results:
        for p in results:
            caps = ", ".join(p.capabilities)
            print(f"  - {p.name} [{caps}]")
            print(f"    {p.description}")
    else:
        print("  (无结果)")
    print()

print("=" * 60)
print("测试完成")
