"""
GraphRAG — SQLite 图存储核心

移植自 MiroFish 项目的 local_graph_store.py（已去除 OASIS/Zep 依赖）。

Schema (4 张表):
  - graphs(graph_id, name, description, ontology, created_at)
  - nodes(uuid, graph_id, name, labels, summary, attributes, created_at)
  - edges(uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, attributes, created_at)
  - episodes(uuid, graph_id, type, data, created_at)
"""

import sqlite3
import json
import uuid as uuid_module
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# 图谱数据存储根目录（项目根 data/graphs/）
GRAPH_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "graphs"
)


class GraphStore:
    """SQLite 图存储核心。每个图对应一个独立的 ``{graph_id}.db`` 文件。"""

    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        os.makedirs(GRAPH_DATA_DIR, exist_ok=True)
        self._db_path = os.path.join(GRAPH_DATA_DIR, f"{graph_id}.db")
        self._init_schema()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS graphs (
                    graph_id    TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    description TEXT,
                    ontology    TEXT,
                    created_at  TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS nodes (
                    uuid        TEXT PRIMARY KEY,
                    graph_id    TEXT NOT NULL,
                    name        TEXT NOT NULL,
                    labels      TEXT,
                    summary     TEXT,
                    attributes  TEXT,
                    created_at  TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS edges (
                    uuid              TEXT PRIMARY KEY,
                    graph_id          TEXT NOT NULL,
                    name              TEXT,
                    fact              TEXT,
                    source_node_uuid  TEXT NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
                    target_node_uuid  TEXT NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
                    attributes        TEXT,
                    created_at        TEXT NOT NULL,
                    valid_at          TEXT,
                    invalid_at        TEXT,
                    expired_at        TEXT
                );
                CREATE TABLE IF NOT EXISTS episodes (
                    uuid       TEXT PRIMARY KEY,
                    graph_id   TEXT NOT NULL,
                    type       TEXT,
                    data       TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_nodes_gid  ON nodes(graph_id);
                CREATE INDEX IF NOT EXISTS idx_edges_gid  ON edges(graph_id);
                CREATE INDEX IF NOT EXISTS idx_edges_src  ON edges(source_node_uuid);
                CREATE INDEX IF NOT EXISTS idx_edges_tgt  ON edges(target_node_uuid);
            """)
        finally:
            conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _new_uuid() -> str:
        return uuid_module.uuid4().hex

    @staticmethod
    def _j(v: Any) -> Optional[str]:
        return None if v is None else json.dumps(v, ensure_ascii=False)

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for field in ["labels", "attributes"]:
            raw = d.get(field)
            if raw:
                try:
                    d[field] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    d[field] = [] if field == "labels" else {}
            else:
                d[field] = [] if field == "labels" else {}
        return d

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        raw = d.get("attributes")
        d["attributes"] = json.loads(raw) if raw else {}
        return d

    # ------------------------------------------------------------------
    # Graph CRUD
    # ------------------------------------------------------------------

    def create_graph(self, name: str, description: str = "",
                     ontology: Optional[Dict] = None) -> Dict[str, Any]:
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO graphs (graph_id, name, description, ontology, created_at) VALUES (?, ?, ?, ?, ?)",
                (self.graph_id, name, description, self._j(ontology), now),
            )
        return {"graph_id": self.graph_id, "name": name, "description": description,
                "ontology": ontology or {}, "created_at": now}

    def clear_all(self):
        """清空当前图的所有数据（幂等，用于重新构建）。"""
        with self._conn() as conn:
            conn.executescript("DELETE FROM edges; DELETE FROM nodes; DELETE FROM episodes; DELETE FROM graphs;")

    def get_graph(self) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM graphs WHERE graph_id = ?", (self.graph_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("ontology"):
            try:
                d["ontology"] = json.loads(d["ontology"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def add_node(self, name: str, labels: Optional[List[str]] = None,
                 summary: str = "", attributes: Optional[Dict] = None) -> Dict[str, Any]:
        node_uuid = self._new_uuid()
        now = self._now()
        labels = labels or ["Entity"]
        attrs = attributes or {}
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO nodes (uuid, graph_id, name, labels, summary, attributes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (node_uuid, self.graph_id, name, self._j(labels), summary, self._j(attrs), now),
            )
        return {"uuid": node_uuid, "graph_id": self.graph_id, "name": name,
                "labels": labels, "summary": summary, "attributes": attrs, "created_at": now}

    def add_nodes_batch(self, nodes: List[Dict]) -> List[Dict[str, Any]]:
        """批量添加节点（单事务）。每项含 name, labels, summary, attributes。
           如果预生成了 uuid 可以传入，否则自动生成。"""
        if not nodes:
            return []
        now = self._now()
        rows = []
        for n in nodes:
            uid = n.get("uuid") or self._new_uuid()
            labels = n.get("labels") or ["Entity"]
            rows.append((uid, self.graph_id, n["name"],
                         self._j(labels), n.get("summary", ""),
                         self._j(n.get("attributes", {})), now))
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO nodes (uuid, graph_id, name, labels, summary, attributes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows)
        return [{"uuid": r[0], "graph_id": r[1], "name": r[2], "labels": json.loads(r[3]) if r[3] else [],
                 "summary": r[4], "attributes": json.loads(r[5]) if r[5] else {}, "created_at": r[6]} for r in rows]

    def get_node(self, node_uuid: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE uuid = ? AND graph_id = ?",
                               (node_uuid, self.graph_id)).fetchone()
        return self._row_to_node(row) if row else None

    def get_node_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT * FROM nodes WHERE graph_id = ? AND name = ?",
                                   (self.graph_id, name)).fetchone()
            return self._row_to_node(row) if row else None
        except Exception as e:
            print(f"[store] get_node_by_name error: {e}")
            return None

    def get_nodes_by_label(self, label: str) -> List[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT n.* FROM nodes n, json_each(n.labels) AS je
                       WHERE n.graph_id = ? AND je.value = ? ORDER BY n.created_at""",
                    (self.graph_id, label)).fetchall()
            return [self._row_to_node(r) for r in rows]
        except Exception as e:
            print(f"[store] get_nodes_by_label error: {e}")
            return []

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                rows = conn.execute("SELECT * FROM nodes WHERE graph_id = ? ORDER BY created_at",
                                    (self.graph_id,)).fetchall()
            return [self._row_to_node(r) for r in rows]
        except Exception as e:
            print(f"[store] get_all_nodes error: {e}")
            return []

    def search_nodes(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        words = [w.strip() for w in keywords.split() if w.strip()]
        if not words:
            return []
        conditions = " OR ".join(["(n.name LIKE ? OR n.summary LIKE ? OR n.labels LIKE ?)" for _ in words])
        params = [self.graph_id]
        for w in words:
            like = f"%{w}%"
            params.extend([like, like, like])
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT n.* FROM nodes n WHERE n.graph_id = ? AND ({conditions}) LIMIT ?",
                params
            ).fetchall()
        return [self._row_to_node(r) for r in rows]

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def add_edge(self, name: str, fact: str, source_node_uuid: str, target_node_uuid: str,
                 attributes: Optional[Dict] = None) -> Dict[str, Any]:
        edge_uuid = self._new_uuid()
        now = self._now()
        attrs = attributes or {}
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO edges (uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, attributes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (edge_uuid, self.graph_id, name, fact, source_node_uuid, target_node_uuid, self._j(attrs), now),
            )
        return {"uuid": edge_uuid, "graph_id": self.graph_id, "name": name, "fact": fact,
                "source_node_uuid": source_node_uuid, "target_node_uuid": target_node_uuid,
                "attributes": attrs, "created_at": now}

    def add_edges_batch(self, edges: List[Dict]) -> List[Dict[str, Any]]:
        """批量添加边（单事务）。每项含 name, fact, source_node_uuid, target_node_uuid。"""
        if not edges:
            return []
        now = self._now()
        rows = []
        for e in edges:
            uid = self._new_uuid()
            rows.append((uid, self.graph_id, e.get("name", ""), e.get("fact", ""),
                         e["source_node_uuid"], e["target_node_uuid"],
                         self._j(e.get("attributes", {})), now))
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO edges (uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, attributes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows)
        return [{"uuid": r[0], "graph_id": r[1], "name": r[2], "fact": r[3],
                 "source_node_uuid": r[4], "target_node_uuid": r[5],
                 "attributes": json.loads(r[6]) if r[6] else {}, "created_at": r[7]} for r in rows]

    def get_all_edges(self) -> List[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                rows = conn.execute("SELECT * FROM edges WHERE graph_id = ? ORDER BY created_at",
                                    (self.graph_id,)).fetchall()
            return [self._row_to_edge(r) for r in rows]
        except Exception as e:
            print(f"[store] get_all_edges error: {e}")
            return []

    def get_edges_for_node(self, node_uuid: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM edges WHERE graph_id = ? AND (source_node_uuid = ? OR target_node_uuid = ?) ORDER BY created_at",
                (self.graph_id, node_uuid, node_uuid)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_edges_between(self, node_uuid_a: str, node_uuid_b: str) -> List[Dict[str, Any]]:
        """获取两个节点之间的直接边。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM edges WHERE graph_id = ? AND ((source_node_uuid = ? AND target_node_uuid = ?) OR (source_node_uuid = ? AND target_node_uuid = ?)) ORDER BY created_at",
                (self.graph_id, node_uuid_a, node_uuid_b, node_uuid_b, node_uuid_a)).fetchall()
        return [self._row_to_edge(r) for r in rows]

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def update_node_summary(self, node_uuid: str, summary: str):
        """更新节点简介。"""
        try:
            with self._conn() as conn:
                conn.execute("UPDATE nodes SET summary = ? WHERE uuid = ? AND graph_id = ?",
                            (summary, node_uuid, self.graph_id))
        except Exception as e:
            print(f"[store] update_node_summary error: {e}")

    def update_node_name(self, node_uuid: str, name: str):
        """更新节点名称。"""
        try:
            with self._conn() as conn:
                conn.execute("UPDATE nodes SET name = ? WHERE uuid = ? AND graph_id = ?",
                            (name, node_uuid, self.graph_id))
        except Exception as e:
            print(f"[store] update_node_name error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        try:
            stats = {"graph_id": self.graph_id, "total_nodes": 0, "total_edges": 0}
            with self._conn() as conn:
                stats["total_nodes"] = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE graph_id = ?", (self.graph_id,)).fetchone()[0]
                stats["total_edges"] = conn.execute(
                    "SELECT COUNT(*) FROM edges WHERE graph_id = ?", (self.graph_id,)).fetchone()[0]
            return stats
        except Exception as e:
            print(f"[store] get_statistics error: {e}")
            return {"graph_id": self.graph_id, "total_nodes": 0, "total_edges": 0}

    def merge_nodes(self, source_uuid: str, target_uuid: str) -> bool:
        """将源节点合并到目标节点：重映射所有边 → 删除重复边 → 删除源节点。"""
        try:
            with self._conn() as conn:
                # 1. 重映射所有从源节点出发的边
                conn.execute("UPDATE edges SET source_node_uuid = ? WHERE source_node_uuid = ? AND graph_id = ?",
                            (target_uuid, source_uuid, self.graph_id))
                # 2. 重映射所有指向源节点的边
                conn.execute("UPDATE edges SET target_node_uuid = ? WHERE target_node_uuid = ? AND graph_id = ?",
                            (target_uuid, source_uuid, self.graph_id))
                # 3. 删除自指边（合并后 source==target 的边无意义）
                conn.execute("DELETE FROM edges WHERE source_node_uuid = target_node_uuid AND graph_id = ?",
                            (self.graph_id,))
                # 4. 删除重复边（相同 source/target/name 的只留一条）
                conn.execute("""
                    DELETE FROM edges WHERE rowid NOT IN (
                        SELECT MIN(rowid) FROM edges
                        WHERE graph_id = ? GROUP BY source_node_uuid, target_node_uuid, name
                    ) AND graph_id = ?
                """, (self.graph_id, self.graph_id))
                # 5. 删除源节点
                conn.execute("DELETE FROM nodes WHERE uuid = ? AND graph_id = ?",
                            (source_uuid, self.graph_id))
            return True
        except Exception as e:
            print(f"[store] merge_nodes error: {e}")
            return False
