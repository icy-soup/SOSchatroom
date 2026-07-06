"""在已有图谱上补跑关系推断 + 全量摘要整理。
使用前建议备份 DB: copy data\graphs\haruhi_novel.db data\graphs\haruhi_novel_backup.db
用法: python backend/scripts/finalize_graph.py
"""
import sys, os, shutil
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 备份
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "graphs" / "haruhi_novel.db"
backup = DB_PATH.with_suffix(".db.backup")
if not backup.exists():
    shutil.copy2(DB_PATH, backup)
    print(f"已备份: {backup}")

from graphrag.builder import GraphBuilder

builder = GraphBuilder("haruhi_novel")
stats = builder.store.get_statistics()
print(f"当前图谱: {stats['total_nodes']} 节点 · {stats['total_edges']} 边")

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
print(f"完成: {stats['total_nodes']} 节点 · {stats['total_edges']} 边")
