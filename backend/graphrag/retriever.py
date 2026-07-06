"""
GraphRAG — 对话时图谱检索器

给定用户消息和当前角色，从图谱中检索最相关的上下文。
每轮对话动态调用，保证 LLM 看到的是新鲜的相关内容。
"""

from typing import Dict, List, Optional, Set, Tuple
from .store import GraphStore


class GraphRetriever:
    """图谱检索器。

    用法:
        retriever = GraphRetriever("haruhi_novel")
        context = retriever.retrieve("春日，外星人到底是不是真的？", "凉宫春日")
    """

    def __init__(self, graph_id: str = "haruhi_novel"):
        self.store = GraphStore(graph_id)
        # 缓存节点名称→uuid 映射，避免反复查询
        self._node_cache: Optional[Dict[str, str]] = None

    def _build_node_cache(self):
        """构建名称→uuid 映射缓存。"""
        if self._node_cache is not None:
            return
        self._node_cache = {}
        for node in self.store.get_all_nodes():
            self._node_cache[node["name"]] = node["uuid"]

    def get_node_by_name(self, name: str) -> Optional[Dict]:
        """按名称获取节点（走缓存）。"""
        self._build_node_cache()
        uuid = self._node_cache.get(name)
        if uuid:
            return self.store.get_node(uuid)
        return None

    def retrieve(self, message: str, character: str = "",
                 max_nodes: int = 8, max_edges: int = 15) -> str:
        """检索与消息最相关的图谱上下文。

        Args:
            message: 用户消息
            character: 当前说话的角色名（用于获取角色相关的上下文）
            max_nodes: 最大返回节点数
            max_edges: 最大返回边数

        Returns:
            格式化的上下文字符串，可直接插入 system prompt
        """
        self._build_node_cache()
        if not self._node_cache:
            return ""

        # 1. 从消息中提取关键词
        keywords = self._extract_keywords(message)

        # 2. 搜索匹配的节点
        matched_nodes: Set[str] = set()

        # 2a. 角色相关的节点（当前角色的关系网络）
        if character and character in self._node_cache:
            char_uuid = self._node_cache[character]
            char_edges = self.store.get_edges_for_node(char_uuid)
            for edge in char_edges:
                other_uuid = edge["source_node_uuid"] if edge["target_node_uuid"] == char_uuid else edge["target_node_uuid"]
                other_node = self.store.get_node(other_uuid)
                if other_node and other_node["name"] not in matched_nodes:
                    matched_nodes.add(other_node["name"])
                if len(matched_nodes) >= max_nodes // 2:
                    break

        # 2b. 关键词搜索
        for kw in keywords:
            results = self.store.search_nodes(kw, limit=3)
            for r in results:
                if r["name"] not in matched_nodes:
                    matched_nodes.add(r["name"])

        # 2c. 把当前角色也加上（如果不在）
        if character and character not in matched_nodes:
            matched_nodes.add(character)

        # 限制数量
        matched_nodes = set(list(matched_nodes)[:max_nodes])

        if not matched_nodes:
            return ""

        # 3. 收集相关边
        node_uuids = {name: uuid for name, uuid in self._node_cache.items() if name in matched_nodes}
        edge_texts: List[str] = []
        seen_edge_keys: Set[Tuple[str, str, str]] = set()

        # 角色优先：都跟当前角色有关
        if character and character in node_uuids:
            char_uuid = node_uuids[character]
            for edge in self.store.get_edges_for_node(char_uuid):
                src = self.store.get_node(edge["source_node_uuid"])
                tgt = self.store.get_node(edge["target_node_uuid"])
                if src and tgt:
                    key = (src["name"], tgt["name"], edge.get("name", ""))
                    if key not in seen_edge_keys:
                        seen_edge_keys.add(key)
                        edge_texts.append(f"  {src['name']} —[{edge.get('name','')}]→ {tgt['name']}: {edge.get('fact','')}")
                        if len(edge_texts) >= max_edges:
                            break

        # 节点之间的边
        if len(edge_texts) < max_edges:
            for name_a, uuid_a in node_uuids.items():
                for name_b, uuid_b in node_uuids.items():
                    if name_a >= name_b:
                        continue
                    for edge in self.store.get_edges_between(uuid_a, uuid_b):
                        key = (name_a, name_b, edge.get("name", ""))
                        if key not in seen_edge_keys:
                            seen_edge_keys.add(key)
                            edge_texts.append(f"  {name_a} —[{edge.get('name','')}]→ {name_b}: {edge.get('fact','')}")
                            if len(edge_texts) >= max_edges:
                                break
                if len(edge_texts) >= max_edges:
                    break

        # 4. 格式化输出
        parts = ["[当前相关背景（来自小说知识图谱）]"]

        # 角色描述
        if character and character in node_uuids:
            node = self.store.get_node(node_uuids[character])
            if node:
                labels = node.get("labels", [])
                parts.append(f"你: {character} ({', '.join(labels[1:])})")

        # 相关人物/实体
        related_names = [n for n in matched_nodes if n != character]
        if related_names:
            parts.append(f"\n相关人物/实体:")
            for name in related_names[:5]:
                node = self.store.get_node(node_uuids[name])
                if node:
                    summary = node.get("summary", "") or ""
                    parts.append(f"  - {name}: {summary[:40]}")

        # 关系
        if edge_texts:
            parts.append(f"\n已知关系:")
            parts.extend(edge_texts[:8])

        return "\n".join(parts)

    def get_character_context(self, character: str) -> str:
        """获取角色的完整背景（用于初始化时加载）。"""
        self._build_node_cache()
        if character not in self._node_cache:
            return ""

        uuid = self._node_cache[character]
        node = self.store.get_node(uuid)
        if not node:
            return ""

        edges = self.store.get_edges_for_node(uuid)

        parts = [f"[{character} 的关系网络]"]
        for edge in edges:
            src = self.store.get_node(edge["source_node_uuid"])
            tgt = self.store.get_node(edge["target_node_uuid"])
            if src and tgt:
                other = tgt if src["uuid"] == uuid else src
                if other["name"] != character:
                    parts.append(f"  {edge.get('name','')}: {other['name']} — {edge.get('fact','')}")

        return "\n".join(parts[:20])

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本中提取关键词。"""
        # 常见无意义词
        stop_words = {"的", "了", "是", "在", "我", "你", "他", "她", "它",
                      "们", "这", "那", "就", "也", "都", "和", "与", "或",
                      "不", "很", "有", "吗", "啊", "呢", "吧", "么", "什么",
                      "怎么", "为什么", "一个", "没有", "不是", "这个", "那个",
                      "可以", "知道", "觉得", "说", "看", "想", "要", "会",
                      "能", "做", "到", "去", "来", "上", "下", "大", "小"}

        import re
        # 只保留中文和英文单词
        tokens = re.findall(r'[一-鿿]+|[a-zA-Z]+', text)
        keywords = [t for t in tokens if t not in stop_words and len(t) > 1]
        return keywords[:10]
