"""在已有图谱上补跑关系推断 + 全量摘要整理。

用法:
    python backend/scripts/finalize_graph.py <graph_id>

示例:
    python backend/scripts/finalize_graph.py haruhi_novel
    python backend/scripts/finalize_graph.py backup_20260706
"""
import sys, os, shutil
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 解析 graph_id
if len(sys.argv) < 2:
    print("用法: python backend/scripts/finalize_graph.py <graph_id>")
    print("示例: python backend/scripts/finalize_graph.py haruhi_novel")
    sys.exit(1)

graph_id = sys.argv[1]

from graphrag.builder import GraphBuilder, _write_status

builder = GraphBuilder(graph_id)
stats = builder.store.get_statistics()
print(f"图谱「{graph_id}」: {stats['total_nodes']} 节点 · {stats['total_edges']} 边")

if stats["total_nodes"] == 0:
    print("图谱为空，无需处理")
    sys.exit(0)

# 1. 关系推断
if stats["total_nodes"] > 5:
    print("开始关系推断...")
    inferred, _ = builder._infer_relationships()
    print(f"  新增 {inferred} 条边")

# 2. 全量摘要整理
stats = builder.store.get_statistics()
print("开始全量摘要整理...")
finalized = builder._finalize_summaries()
print(f"  更新 {finalized} 个节点摘要")

stats = builder.store.get_statistics()
_write_status(graph_id, {"status": "completed", "progress": 1.0,
                         "nodes": stats["total_nodes"], "edges": stats["total_edges"],
                         "message": f"已完成推断+摘要整理 · {stats['total_nodes']}节点 · {stats['total_edges']}边"})
print(f"完成: {stats['total_nodes']} 节点 · {stats['total_edges']} 边")
