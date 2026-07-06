"""
已有图谱去重脚本：在 haruhi_novel.db 上直接跑别名合并 + 黑名单过滤，
不需要重新调用 LLM 构建。
"""

import sys, os, sqlite3, json
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from graphrag.builder import resolve_name, BLOCKLIST

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "graphs", "haruhi_novel.db")
GRAPH_ID = "haruhi_novel"

def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # 1. 读取所有节点
    nodes = conn.execute(
        "SELECT uuid, name, labels FROM nodes WHERE graph_id = ?", (GRAPH_ID,)
    ).fetchall()
    print(f"去重前: {len(nodes)} 节点")

    # 2. 分组
    groups = defaultdict(list)
    name_to_uuids = defaultdict(set)
    blocked = []

    for n in nodes:
        canon = resolve_name(n["name"])
        if canon in BLOCKLIST:
            blocked.append(n["uuid"])
            print(f"  黑名单过滤: {n['name']}")
            continue
        groups[canon].append(n)
        name_to_uuids[canon].add(n["uuid"])

    # 3. 读取所有边
    edges = conn.execute(
        "SELECT uuid, source_node_uuid, target_node_uuid, name, fact FROM edges WHERE graph_id = ?",
        (GRAPH_ID,),
    ).fetchall()
    print(f"去重前: {len(edges)} 边")

    # 4. 合并重复节点
    merged_count = 0
    rename_count = 0

    for canon, group in groups.items():
        if len(group) > 1:
            # 选第一个写入的作为幸存者
            group.sort(key=lambda n: n["uuid"])
            survivor = group[0]
            dead = group[1:]

            # 更新幸存者 name（如果有规范名变化）
            if survivor["name"] != canon:
                conn.execute(
                    "UPDATE nodes SET name = ? WHERE uuid = ?", (canon, survivor["uuid"])
                )
                rename_count += 1

            for d in dead:
                dead_uuid = d["uuid"]
                # 把指向 dead 节点的边重指向 survivor
                conn.execute(
                    "UPDATE edges SET source_node_uuid = ? WHERE source_node_uuid = ? AND graph_id = ?",
                    (survivor["uuid"], dead_uuid, GRAPH_ID),
                )
                conn.execute(
                    "UPDATE edges SET target_node_uuid = ? WHERE target_node_uuid = ? AND graph_id = ?",
                    (survivor["uuid"], dead_uuid, GRAPH_ID),
                )
                # 删除 self-loop（source=target 且都指向同一个人）
                conn.execute(
                    "DELETE FROM edges WHERE source_node_uuid = target_node_uuid AND source_node_uuid = ? AND graph_id = ?",
                    (survivor["uuid"], GRAPH_ID),
                )
                # 删除 dead 节点
                conn.execute("DELETE FROM nodes WHERE uuid = ?", (dead_uuid,))
                merged_count += 1
            print(f"  合并: {survivor['name']} ({', '.join(n['name'] for n in group)}) → {canon}")
        elif group[0]["name"] != canon:
            # 单节点但名字变了
            conn.execute(
                "UPDATE nodes SET name = ? WHERE uuid = ?", (canon, group[0]["uuid"])
            )
            rename_count += 1
            print(f"  重命名: {group[0]['name']} → {canon}")

    # 5. 删除黑名单节点的边和节点自身
    if blocked:
        placeholders = ",".join("?" for _ in blocked)
        conn.execute(
            f"DELETE FROM edges WHERE (source_node_uuid IN ({placeholders}) OR target_node_uuid IN ({placeholders})) AND graph_id = ?",
            blocked + blocked + [GRAPH_ID],
        )
        conn.execute(
            f"DELETE FROM nodes WHERE uuid IN ({placeholders}) AND graph_id = ?",
            blocked + [GRAPH_ID],
        )

    # 6. 删除 source=target 的重复自环
    conn.execute(
        """DELETE FROM edges WHERE rowid NOT IN (
               SELECT MIN(rowid) FROM edges
               WHERE graph_id = ? AND source_node_uuid = target_node_uuid
               GROUP BY source_node_uuid, name, fact
           ) AND graph_id = ? AND source_node_uuid = target_node_uuid""",
        (GRAPH_ID, GRAPH_ID),
    )

    # 7. 删除完全重复的边（同 source/target/name/fact）
    conn.execute(
        """DELETE FROM edges WHERE rowid NOT IN (
               SELECT MIN(rowid) FROM edges
               WHERE graph_id = ?
               GROUP BY source_node_uuid, target_node_uuid, name, fact
           ) AND graph_id = ?""",
        (GRAPH_ID, GRAPH_ID),
    )

    conn.commit()

    # 8. 最终统计
    final_nodes = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE graph_id = ?", (GRAPH_ID,)
    ).fetchone()[0]
    final_edges = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE graph_id = ?", (GRAPH_ID,)
    ).fetchone()[0]

    print(f"\n完成: 合并 {merged_count} 节点, 重命名 {rename_count} 节点, 过滤 {len(blocked)} 节点")
    print(f"最终: {final_nodes} 节点, {final_edges} 边")
    conn.close()


if __name__ == "__main__":
    main()
