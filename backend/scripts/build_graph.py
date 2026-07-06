#!/usr/bin/env python3
"""
构建凉宫春日小说知识图谱。

用法:
    python scripts/build_graph.py

读取 data/novels/ 下的 txt 文件（如 txt全卷.txt），构建图谱保存到 data/graphs/haruhi_novel.db。
"""

import sys
import os
from pathlib import Path

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphrag.builder import GraphBuilder


def main():
    novels_dir = Path(__file__).resolve().parent.parent.parent / "data" / "novels"
    if not novels_dir.exists():
        print(f"[错误] 小说目录不存在: {novels_dir}")
        sys.exit(1)

    # 读取所有小说文本
    txt_files = sorted(novels_dir.glob("*.txt"))
    if not txt_files:
        print(f"[错误] 未找到小说文件 (*.txt)")
        sys.exit(1)

    print(f"找到 {len(txt_files)} 个小说文件:")
    full_text = ""
    for f in txt_files:
        size = f.stat().st_size
        print(f"  {f.name} ({size/1024:.0f}KB)")
        text = f.read_text(encoding="utf-8")
        full_text += f"\n\n=== {f.stem} ===\n{text}"
    print(f"\n总字数: {len(full_text):,}")

    # 构建图谱
    print("\n开始构建图谱...")
    builder = GraphBuilder("haruhi_novel")

    def on_progress(msg: str, progress: float):
        bar = int(progress * 20)
        print(f"\r[{('#' * bar).ljust(20)}] {int(progress * 100)}% — {msg}", end="", flush=True)
        if progress >= 1.0:
            print()

    stats = builder.build_from_text(full_text, progress_callback=on_progress)

    print(f"\n图谱构建完成！")
    print(f"  节点: {stats['total_nodes']}")
    print(f"  边: {stats['total_edges']}")
    print(f"  存储: {os.path.join('data', 'graphs', 'haruhi_novel.db')}")


if __name__ == "__main__":
    main()
