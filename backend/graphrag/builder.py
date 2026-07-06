"""
GraphRAG — 图谱构建器

移植自 MiroFish 的 graph_builder.py + entity_extractor.py。
每 5 chunk 增量写入一次 DB，前端轮询可见节点/边实时增长。

修复 MiroFish 问题：
  1. ✅ 硬编码别名映射（阿虚=Kyon=我），不依赖 LLM 猜
  2. ✅ entity 增加 category 字段（person/organization/object）
  3. ✅ 单趟提取，不浪费两趟 LLM
  4. ✅ status.json 实时进度
"""

import json, os, threading, time
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from difflib import get_close_matches
from .store import GraphStore

# 模糊匹配阈值（用于纠正错别字）
FUZZY_CUTOFF = 0.6

# ============================================================
# 别名映射（硬编码）
# ============================================================
ALIAS_MAP = {
    "阿虚": ["阿虚", "虚", "キョン", "Kyon", "kyon", "私", "我", "俺", "僕", "ボク", "オレ"],
    "凉宫春日": ["凉宫春日", "凉宫", "春日", "Haruhi", "haruhi", "团长", "ハルヒ", "凉宫同学", "春日同学"],
    "长门有希": ["长门有希", "长门", "有希", "Yuki", "yuki", "ユキ", "长门同学"],
    "朝比奈实玖瑠": ["朝比奈实玖瑠", "朝比奈", "实玖瑠", "Mikuru", "mikuru", "ミクル", "朝比奈同学", "实玖瑠学姐", "朝比奈学姐"],
    "古泉一树": ["古泉一树", "古泉", "一树", "Itsuki", "itsuki", "古泉君", "転校生", "谜样转学生"],
    "朝仓凉子": ["朝仓凉子", "朝仓", "朝仓同学"],
    "谷口": ["谷口", "谷口君", "谷口くん"],
    "国木田": ["国木田", "国木田君", "国木田くん", "国术田"],  # 国术田是错别字
    "鹤屋": ["鹤屋", "鹤屋さん", "鹤屋学姐", "鹤屋先輩"],
    "三味线": ["三味线", "三味線", "シャミセン"],
    "冈部": ["冈部", "冈部先生", "冈部老师", "冈部导师"],
    "电脑研究社社长": ["电脑研究社社长", "电脑部社长"],
    "喜绿江美里": ["喜绿江美里", "喜绿", "喜绿先生", "喜绿老师", "江美里"],
    "多丸": ["多丸", "多丸先生", "多丸圭一", "多丸裕"],
    "森": ["森", "森小姐", "森さん"],
    "SOS团": ["SOS团", "SOS団", "SOS Brigade", " sos团"],
    "周防九耀": ["周防九耀", "九耀"],
    "妹妹": ["阿虚的妹妹", "妹妹", "我的妹妹", "虚妹", "老妹"],
    "葫芦石": ["葫芦石", "葫芦状的石头"],
}

BLOCKLIST = {"伊东", "伊东杂音", "Noizi Ito", "いとう のいづ", "谷川流",
             "『小长门有希的消失』", "『小凉宫春日的忧郁』"}

# 预定义关系类型（LLM 也可以创建新的中文关系名）
RELATION_TYPES = ["认识","属于","互动","提及","位于","创造","反对","信任",
                  "亲属","拥有","使用","穿着","参与"]
RELATION_ALIAS = {"KNOWS":"认识","MEMBER_OF":"属于","INTERACTS_WITH":"互动","MENTIONS":"提及",
                  "LOCATED_AT":"位于","CREATES":"创造","OPPOSES":"反对","TRUSTS":"信任",
                  "RELATIVE":"亲属","OWNS":"拥有","USES":"使用","WEARS":"穿着","PARTICIPATES_IN":"参与"}

_ALIAS_TO_MAIN = {}
for main_name, aliases in ALIAS_MAP.items():
    for a in aliases:
        _ALIAS_TO_MAIN[a] = main_name

def resolve_name(raw: str) -> str:
    """别名解析：精确匹配 → 模糊匹配(纠错别字) → 子串包含匹配。"""
    clean = raw.strip()
    # 1. 精确匹配
    exact = _ALIAS_TO_MAIN.get(clean)
    if exact:
        return exact
    # 2. 模糊匹配（纠正错别字如"国术田"→"国木田"）
    fuzzy = get_close_matches(clean, list(ALIAS_MAP.keys()), n=1, cutoff=FUZZY_CUTOFF)
    if fuzzy:
        print(f"[builder] 模糊匹配: '{raw}' → '{fuzzy[0]}'")
        return fuzzy[0]
    # 3. 子串匹配：输入是规范名的一部分（如"九耀"→"周防九耀"）
    #    只做 clean in k 方向，不做 k in clean，避免短规范名误吞长名
    if len(clean) >= 2:
        candidates = [k for k in ALIAS_MAP if len(k) >= 2 and clean in k and k != clean]
        if len(candidates) == 1:
            print(f"[builder] 子串匹配: '{raw}' → '{candidates[0]}'")
            return candidates[0]
    return clean

# ============================================================
# LLM Prompt
# ============================================================
EXTRACT_PROMPT = """你是一个凉宫春日系列小说的实体关系抽取器。

实体分类（category，必填）:
  - person: 人物角色（有智能的）。包括: 凉宫春日、阿虚、长门有希、朝比奈实玖瑠、古泉一树、朝仓凉子、鹤屋、谷口、国木田、冈部、喜绿江美里、多丸先生、森小姐、三味线（猫）
  - organization: 社团/学校/机构。如 SOS团、北高、电脑研究社
  - object: 物品/概念/地点/事件（只提取对剧情有意义的）

关系类型（优先从以下选择，如果没有合适的可以创建新的中文关系名，如「亲属」「就读」「赠送」等）:
  认识 / 属于 / 互动 / 提及
  位于 / 创造 / 反对 / 信任
  亲属 / 拥有 / 使用 / 穿着 / 参与

规则:
1. 第一人称「我」「俺」「僕」都指向阿虚，统一输出为"阿虚"
2. 同一人物不同称呼用同一标准名（详见person列表）
3. 如有疑似错别字（如"国术田"可能是"国木田"），用正确的标准名
4. 只提取文本中明确提及的关系
5. 每个实体输出 name, type(描述如"学生""外星人"), category, summary(15字内)
6. 必须提取人物实体，即使只出现名字也要提取
7. 「属于」只能用于 person→organization，不能 person→person
8. 「位于」不能 person→person，其他情况可用（人物位于某地、组织位于某地等均可）

输出JSON: {"entities":[{"name":"","type":"","category":"person/organization/object","summary":""}],"edges":[{"source":"","target":"","name":"关系名","fact":"依据"}]}"""

# ============================================================
# 进度状态
# ============================================================
STATUS_FILE = os.path.join(os.path.dirname(__file__), "build_status.json")
_status_lock = threading.Lock()

def _write_status(graph_id: str, data: dict):
    """写入 nested 状态。graph_id 为 None 时只更新 active_graph_id。"""
    with _status_lock:
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                full = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            full = {"active_graph_id": None, "graphs": {}}
        if "graphs" not in full:
            # 旧格式迁移
            old = {k: full[k] for k in full if k not in ("active_graph_id",)}
            full = {"active_graph_id": None, "graphs": {"haruhi_novel": old}}
        if graph_id:
            full["graphs"][graph_id] = data
        if data.get("status") == "building":
            full["active_graph_id"] = graph_id
        elif data.get("status") in ("completed", "error", "idle") and full.get("active_graph_id") == graph_id:
            full["active_graph_id"] = None
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(full, f, ensure_ascii=False, indent=2)

def read_status(graph_id: str = None) -> dict:
    """读取状态。graph_id=None 返回完整结构，否则返回该图状态。"""
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            full = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        full = {"active_graph_id": None, "graphs": {}}
    if "graphs" not in full:
        # 旧格式迁移：flat dict → nested
        old = {k: full[k] for k in full if k != "active_graph_id"}
        full = {"active_graph_id": None, "graphs": {"haruhi_novel": old}}
    if graph_id:
        return full["graphs"].get(graph_id, {"status": "idle", "progress": 0, "message": "", "nodes": 0, "edges": 0})
    return full

# ============================================================
# 构建器
# ============================================================
class GraphBuilder:
    def __init__(self, graph_id: str = "haruhi_novel"):
        self.graph_id = graph_id
        self.store = GraphStore(graph_id)
        self._llm = None

    def _get_llm(self):
        if self._llm:
            return self._llm
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)
        import re
        def _e(k, d=""): return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', os.environ.get(k, d))
        key = _e("ANTHROPIC_API_KEY")
        url = _e("ANTHROPIC_API_URL", "https://api.deepseek.com")
        model = _e("ANTHROPIC_MODEL", "deepseek-chat")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY 未配置")
        from openai import OpenAI
        import httpx
        http = httpx.Client(timeout=httpx.Timeout(300.0, connect=30.0))
        self._llm = {"client": OpenAI(api_key=key, base_url=url, http_client=http), "model": model}
        return self._llm

    def _call_llm(self, text: str, chunk_idx: int = -1) -> Optional[Dict]:
        for attempt in range(3):
            try:
                llm = self._get_llm()
                tag = f"[#{chunk_idx}]" if chunk_idx >= 0 else ""
                r = llm["client"].chat.completions.create(
                    model=llm["model"],
                    messages=[{"role": "system", "content": EXTRACT_PROMPT},
                              {"role": "user", "content": f"从以下文本中提取实体和关系：\n\n{text[:5000]}"}],
                    response_format={"type": "json_object"}, temperature=0.1, max_tokens=4096)
                result = json.loads(r.choices[0].message.content)
                if attempt > 0:
                    print(f"[builder]{tag} 重试成功")
                return result
            except Exception as e:
                if attempt < 2:
                    print(f"[builder]{tag} API调用失败({attempt+1}/3): {type(e).__name__}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"[builder]{tag} API调用失败(已放弃): {e}")
                    return None

    def build_async(self, text: str, skip_chunks: int = 0):
        """后台线程构建。skip_chunks>0 时跳过已处理的块，用于跨重启继续构建。"""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        _write_status(self.graph_id, {"status":"building","progress":0,"message":"初始化...",
                       "nodes":0,"edges":0,"total_chunks":0,"current_chunk":skip_chunks,"started_at":now})
        print(f"[builder] 构建开始 · {len(text):,} 字符 · 跳过前 {skip_chunks} 块")
        thread = threading.Thread(target=self._build_worker, args=(text, skip_chunks), daemon=True)
        thread.start()

    def _build_worker(self, text: str, skip_chunks: int = 0):
        try:
            self.store.create_graph(name="凉宫春日系列小说", ontology={
                "entity_categories":["person","organization","object"],
                "relation_types":["KNOWS","MEMBER_OF","INTERACTS_WITH","MENTIONS","LOCATED_AT","CREATES","OPPOSES","TRUSTS"]})

            # 分块（4000 字符/块，50 重叠 → ~380 块，比 3000 快 25%）
            chunks = self._split(text, 4000, 50)
            if skip_chunks > 0:
                chunks = chunks[skip_chunks:]  # 跳过已处理的块
            total = len(chunks) + skip_chunks
            _write_status(self.graph_id, {"status":"building", "total_chunks":total, "message":f"文本已分 {total} 块（跳过 {skip_chunks} 块）"})

            # 逐块提取（MiroFish 模式：每 10 块 merge 一次别名）
            written_nodes: set = set()
            written_edge_keys: set = set()
            node_name_to_uuid: Dict[str, str] = {}
            node_category: Dict[str, str] = {}  # name→category
            pending_nodes: List[Dict] = []
            pending_edges: List[Dict] = []
            all_raw_entities: List[Dict] = []  # 原始名（resolve 前），给 merge 用
            flushed_nodes = 0   # 实际写入 DB 的节点数，供前端刷新用
            flushed_edges = 0   # 实际写入 DB 的边数

            def flush_batch():
                nonlocal pending_nodes, pending_edges, flushed_nodes, flushed_edges
                if pending_nodes:
                    self.store.add_nodes_batch(pending_nodes)
                    pending_nodes = []
                    flushed_nodes = len(written_nodes)
                if pending_edges:
                    self.store.add_edges_batch(pending_edges)
                    pending_edges = []
                    flushed_edges = len(written_edge_keys)

            def run_merge():
                """阶段性别名合并：将 raw 名中的变体映射到主 UUID。"""
                nonlocal all_raw_entities
                if len(all_raw_entities) < 2:
                    return
                merged = self._merge_entities(all_raw_entities)
                added = 0
                for main_name, info in merged.items():
                    if not info["aliases"]:
                        continue
                    main_uuid = node_name_to_uuid.get(main_name)
                    if not main_uuid:
                        continue
                    for alias in info["aliases"]:
                        if alias not in node_name_to_uuid:
                            node_name_to_uuid[alias] = main_uuid
                            added += 1
                if added:
                    print(f"[builder]   别名合并: +{added} 映射")
                all_raw_entities = []
            touched_nodes = set()  # 被新边触及的节点，用于增量摘要更新

            for i, chunk in enumerate(chunks):
                while read_status(self.graph_id).get("status") == "paused":
                    time.sleep(1)
                if i % 10 == 0:
                    print(f"[builder] {i}/{total} chunks · {len(written_nodes)} nodes · {len(written_edge_keys)} edges")
                result = self._call_llm(chunk, i)
                if not result:
                    time.sleep(0.5)
                    continue
                # 提取当前块详情，供前端实时显示
                chunk_entities = [resolve_name(e.get("name","")) for e in result.get("entities",[]) if e.get("name","").strip()]
                chunk_edges = [f"{resolve_name(e.get('source',''))}→{e.get('name','')}→{resolve_name(e.get('target',''))}" for e in result.get("edges",[]) if e.get("source","").strip() and e.get("target","").strip()]

                for e in result.get("entities", []):
                    raw_name = e.get("name","").strip()
                    if not raw_name:
                        continue
                    # 存原始名供阶段性 merge 检测变体
                    all_raw_entities.append({"name": raw_name, "type": e.get("type",""), "summary": e.get("summary","")[:20]})
                    name = resolve_name(raw_name)
                    if not name or name in BLOCKLIST or name in written_nodes:
                        continue
                    uuid = node_name_to_uuid.get(name)
                    if not uuid:
                        existing = self.store.get_node_by_name(name)
                        uuid = existing["uuid"] if existing else None
                    if not uuid:
                        import uuid as _uuid
                        uuid = _uuid.uuid4().hex
                        pending_nodes.append({
                            "uuid": uuid,
                            "name": name,
                            "labels": ["Entity", e.get("type","Unknown"), e.get("category","person")],
                            "summary": e.get("summary","")[:30],
                        })
                    node_name_to_uuid[name] = uuid
                    node_category[name] = e.get("category","person")
                    written_nodes.add(name)

                for e in result.get("edges", []):
                    src = resolve_name(e.get("source",""))
                    tgt = resolve_name(e.get("target",""))
                    src_u = node_name_to_uuid.get(src)
                    tgt_u = node_name_to_uuid.get(tgt)
                    if not src_u or not tgt_u:
                        continue
                    # 关系验证：英文→中文，不硬拦新词
                    rel = e.get("name", "")
                    rel = RELATION_ALIAS.get(rel, rel)  # 英文→中文  # 不在允许列表里的直接丢弃
                    src_cat = node_category.get(src, "")
                    tgt_cat = node_category.get(tgt, "")
                    if rel in ("属于", "MEMBER_OF"):
                        if tgt_cat != "organization":
                            continue
                    if rel in ("位于", "LOCATED_AT"):
                        if src_cat == "person" and tgt_cat == "person":
                            continue
                    key = (src_u, tgt_u, rel)
                    if key in written_edge_keys:
                        continue
                    written_edge_keys.add(key)
                    pending_edges.append({
                        "name": rel,
                        "fact": e.get("fact","")[:100],
                        "source_node_uuid": src_u,
                        "target_node_uuid": tgt_u,
                    })
                    touched_nodes.update([src_u, tgt_u])

                flush_batch()  # 每块即时写入，保证前端实时刷新
                if (i+1) % 10 == 0:
                    run_merge()
                    # 每 10 块增量更新被新边触及的节点的摘要
                    updated = self._update_summaries_for_nodes(touched_nodes)
                    if updated:
                        print(f"[builder]   摘要更新: {updated} 节点")
                    touched_nodes.clear()

                _cur = read_status(self.graph_id)
                _db_stats = self.store.get_statistics()
                _write_status(self.graph_id, {
                    "status": "paused" if _cur.get("status") == "paused" else "building",
                    "progress": round(0.05 + (i+1+skip_chunks)/total*0.9, 3),
                    "current_chunk": i+1+skip_chunks, "total_chunks": total,
                    "nodes": _db_stats["total_nodes"],
                    "edges": _db_stats["total_edges"],
                    "message": f"块 {i+1+skip_chunks}/{total} · {_db_stats['total_nodes']} 节点 · {_db_stats['total_edges']} 边",
                    "chunk_entities": chunk_entities[:8],
                    "chunk_edges": chunk_edges[:4],
                })
            flush_batch()
            run_merge()  # 最后一轮别名合并

            # 跨块关系推断
            stats = self.store.get_statistics()
            if stats['total_nodes'] > 5:
                inferred, inf_touched = self._infer_relationships()
                if inferred:
                    print(f"[builder] 关系推断完成: +{inferred} 边")
                touched_nodes.update(inf_touched)

            # 最终更新：被推断新边触及的节点 + 块处理剩余节点
            if touched_nodes:
                updated = self._update_summaries_for_nodes(touched_nodes)
                if updated:
                    print(f"[builder] 摘要更新: {updated} 节点")

            # 全量整理：对所有有边的节点重新组织摘要（去重、按重要度排序、删琐碎）
            finalized = self._finalize_summaries()
            if finalized:
                print(f"[builder] 摘要全量整理: {finalized} 节点")

            stats = self.store.get_statistics()
            print(f"[builder] 完成 · {stats['total_nodes']}·{stats['total_edges']}边")
            _write_status(self.graph_id, {
                "status":"completed","progress":1.0,"current_chunk":total,"total_chunks":total,
                "nodes":stats["total_nodes"],"edges":stats["total_edges"],
                "message":f"构建完成 · {stats['total_nodes']} 节点 · {stats['total_edges']} 边",
            })
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[builder] 错误: {e}")
            print(tb)
            _write_status(self.graph_id, {"status":"error",
                          "message":f"失败: {str(e)}", "error": tb})

    @staticmethod
    def _split(text: str, size: int, overlap: int) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start+size, len(text))
            if end < len(text):
                nl = text.rfind('\n', start, end)
                if nl > start + size//2:
                    end = nl
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end
        return chunks

    def _merge_entities(self, all_entities: List[Dict]) -> Dict[str, Dict]:
        """用 LLM 合并别名。返回 {main_name: {entity, aliases}}。"""
        if not all_entities:
            return {}
        name_to_entity = {}
        for e in all_entities:
            n = e.get("name","")
            if n and n not in name_to_entity:
                name_to_entity[n] = e
        if len(name_to_entity) <= 1:
            return {n: {"entity": e, "aliases": []} for n, e in name_to_entity.items()}

        prompt = (
            "你是一个实体对齐专家。判断以下实体名称是否指向现实中的同一个对象。\n"
            "规则：\n"
            "1. 昵称、别名、不同语言的译名指向同一人，应当合并\n"
            "2. 第一人称指向其所属的叙述者身份\n"
            "3. 仅合并确定是同一实体的项\n"
            "输出JSON: {\"merge_groups\": [{\"main\": \"正式名称\", \"aliases\": [\"别名1\", \"别名2\"], \"reason\": \"原因\"}]}"
        )
        entities_for_llm = [{"name": e["name"], "type": e.get("type",""), "summary": e.get("summary","")} for e in name_to_entity.values()]
        try:
            llm = self._get_llm()
            r = llm["client"].chat.completions.create(
                model=llm["model"],
                messages=[{"role": "system", "content": prompt},
                          {"role": "user", "content": json.dumps(entities_for_llm, ensure_ascii=False)}],
                response_format={"type": "json_object"}, temperature=0.1, max_tokens=2048)
            result = json.loads(r.choices[0].message.content)
        except Exception as e:
            print(f"[builder] 别名合并LLM调用失败: {e}")
            return {n: {"entity": e, "aliases": []} for n, e in name_to_entity.items()}

        merged = {}
        assigned = set()
        for group in (result.get("merge_groups") or []):
            main = (group.get("main") or "").strip()
            if not main or main not in name_to_entity or main in assigned:
                continue
            aliases = [a for a in (group.get("aliases") or []) if isinstance(a, str) and a.strip() and a != main and a not in assigned and a in name_to_entity]
            merged[main] = {"entity": name_to_entity[main], "aliases": aliases}
            assigned.add(main)
            assigned.update(aliases)

        for n, e in name_to_entity.items():
            if n not in assigned:
                merged[n] = {"entity": e, "aliases": []}
        return merged

    def _infer_relationships(self) -> tuple:
        """跨块关系推断：对所有节点批量 LLM 推断缺失的边。"""
        nodes = self.store.get_all_nodes()
        if len(nodes) < 2:
            return 0

        # 建立名称→UUID 缓存
        name_to_uuid = {n["name"]: n["uuid"] for n in nodes}

        # 收集已有边 pair（标准化排序，忽略方向）
        existing_edges = self.store.get_all_edges()
        existing_pairs: set = set()
        node_map = {n["uuid"]: n["name"] for n in nodes}
        for e in existing_edges:
            sn = node_map.get(e["source_node_uuid"])
            tn = node_map.get(e["target_node_uuid"])
            if sn and tn:
                existing_pairs.add(tuple(sorted([sn, tn])))

        # 构造实体列表（按 category 分组，个人优先）
        persons = []
        organizations = []
        objects = []
        for n in nodes:
            labels = n.get("labels", [])
            cat = labels[2] if len(labels) > 2 else "object"
            entry = {"name": n["name"], "category": cat, "summary": n.get("summary", "")[:20]}
            if cat == "person":
                persons.append(entry)
            elif cat == "organization":
                organizations.append(entry)
            else:
                objects.append(entry)

        all_entries = persons + organizations + objects
        batch_size = 25
        new_count = 0
        inference_touched = set()

        prompt = (
            "你是凉宫春日系列小说的关系推断专家。\n"
            "已知以下实体列表（人物/组织/物品），推断它们之间有哪些已知关系。\n"
            "规则：\n"
            "1. 只推断你确定存在于凉宫春日小说中的关系\n"
            "2. 人物之间的社交关系（认识/信任/反对）\n"
            "3. 人物对组织的归属（属于）\n"
            "4. 人物对物品的所有或创建（创造/拥有/使用）\n"
            "5. 人物之间的互动（互动/提及）\n"
            "6. 人物之间的亲属关系（亲属）\n"
            "7. 人物穿着/持有某物（穿着/拥有）\n"
            "8. 只输出新关系，不要在已有常识关系上遗漏\n"
            "关系类型优先从「认识/属于/互动/提及/位于/创造/反对/信任/亲属/拥有/使用/穿着/参与」中选择，也可以创建新的中文关系名。\n"
            "输出JSON: {\"edges\": [{\"source\":\"实体名\",\"target\":\"实体名\",\"name\":\"关系类型\",\"fact\":\"依据描述(15字内)\"}]}"
        )

        for start in range(0, len(all_entries), batch_size):
            batch = all_entries[start:start + batch_size]
            total_batches = (len(all_entries) - 1) // batch_size + 1
            _write_status(self.graph_id, {"message": f"关系推断中 ({start//batch_size+1}/{total_batches})..."})
            result = None
            for attempt in range(3):
                try:
                    llm = self._get_llm()
                    r = llm["client"].chat.completions.create(
                        model=llm["model"],
                        messages=[{"role": "system", "content": prompt},
                                  {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}],
                        response_format={"type": "json_object"}, temperature=0.1, max_tokens=2048)
                    result = json.loads(r.choices[0].message.content)
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"[builder] 关系推断重试(batch {start}, {attempt+1}/3): {e}")
                        time.sleep(2 ** attempt)
                    else:
                        print(f"[builder] 关系推断失败(batch {start}, 已放弃): {e}")
            if result is None:
                continue

            batch_edges = []
            for edge in result.get("edges", []):
                src = resolve_name(edge.get("source", ""))
                tgt = resolve_name(edge.get("target", ""))
                if not src or not tgt or src == tgt:
                    continue
                pair = tuple(sorted([src, tgt]))
                if pair in existing_pairs:
                    continue
                src_u = name_to_uuid.get(src)
                tgt_u = name_to_uuid.get(tgt)
                if not src_u or not tgt_u:
                    continue
                existing_pairs.add(pair)
                batch_edges.append({
                    "name": edge.get("name", "RELATED"),
                    "fact": edge.get("fact", "")[:100],
                    "source_node_uuid": src_u,
                    "target_node_uuid": tgt_u,
                })

            if batch_edges:
                self.store.add_edges_batch(batch_edges)
                new_count += len(batch_edges)
                for e in batch_edges:
                    inference_touched.update([e["source_node_uuid"], e["target_node_uuid"]])
                print(f"[builder]   关系推断(batch {start//batch_size+1}): +{len(batch_edges)} 边")

        return new_count, inference_touched

    def _update_summaries_for_nodes(self, node_uuids: set) -> int:
        """增量更新节点摘要：根据节点当前所有边的信息，去重合并后更新 summary。"""
        if not node_uuids:
            return 0
        nodes_data = []
        all_nodes = {n["uuid"]: n for n in self.store.get_all_nodes()}
        all_edges = self.store.get_all_edges()
        # 建立每条边的可读表述
        edge_lines = []
        for e in all_edges:
            sn = all_nodes.get(e["source_node_uuid"], {}).get("name", "?")
            tn = all_nodes.get(e["target_node_uuid"], {}).get("name", "?")
            if sn == "?" or tn == "?":
                continue
            edge_lines.append((e["source_node_uuid"], e["target_node_uuid"],
                               f"{sn} ─[{e.get('name','')}]→ {tn}: {e.get('fact','')}"))
        for uid in node_uuids:
            n = all_nodes.get(uid)
            if not n:
                continue
            related = [l for l in edge_lines if l[0] == uid or l[1] == uid]
            if not related:
                continue
            nodes_data.append((n["name"], n.get("summary", ""), [l[2] for l in related]))
        if not nodes_data:
            return 0
        updated = 0
        batch_size = 10
        for start in range(0, len(nodes_data), batch_size):
            batch = nodes_data[start:start + batch_size]
            lines = []
            for name, summary, edges in batch:
                lines.append(f"节点: {name}")
                lines.append(f"当前简介: {summary or '(无)'}")
                lines.append("关联关系:")
                for e in edges[:20]:  # 最多 20 条边，防止太长
                    lines.append(f"  {e}")
                lines.append("")
            prompt = (
                "以下是凉宫春日系列图谱中的节点及其当前简介、关联关系。\n"
                "请为每个节点重新生成简介：合并旧简介和新关系中的信息，去重，不删已有内容。\n"
                "直接输出JSON: {\"summaries\": [{\"node\":\"节点名\",\"summary\":\"更新后的简介\"}]}\n\n"
                + "\n".join(lines)
            )
            try:
                llm = self._get_llm()
                r = llm["client"].chat.completions.create(
                    model=llm["model"],
                    messages=[{"role": "system", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.1, max_tokens=2048)
                result = json.loads(r.choices[0].message.content)
                for item in result.get("summaries", []):
                    name = item.get("node", "")
                    summary = item.get("summary", "")
                    if not name or not summary:
                        continue
                    # 找到对应 UUID
                    for uid in node_uuids:
                        n = all_nodes.get(uid)
                        if n and n["name"] == name:
                            self.store.update_node_summary(uid, summary)
                            updated += 1
                            break
            except Exception as e:
                print(f"[builder] 摘要更新失败(batch {start}): {e}")
                continue
        return updated

    def _finalize_summaries(self) -> int:
        """全量整理所有有边节点的摘要：去重、按重要度排序、删除琐碎信息。"""
        all_nodes = {n["uuid"]: n for n in self.store.get_all_nodes()}
        all_edges = self.store.get_all_edges()
        degree = {}
        for e in all_edges:
            degree[e["source_node_uuid"]] = degree.get(e["source_node_uuid"], 0) + 1
            degree[e["target_node_uuid"]] = degree.get(e["target_node_uuid"], 0) + 1
        # 只处理有边的节点，按度排序（重要的优先）
        nodes_with_edges = [(uid, n) for uid, n in all_nodes.items() if degree.get(uid, 0) > 0]
        nodes_with_edges.sort(key=lambda x: degree.get(x[0], 0), reverse=True)
        if not nodes_with_edges:
            return 0
        # 建立每条边的可读表述
        edge_lines = []
        for e in all_edges:
            sn = all_nodes.get(e["source_node_uuid"], {}).get("name", "?")
            tn = all_nodes.get(e["target_node_uuid"], {}).get("name", "?")
            if sn == "?" or tn == "?":
                continue
            edge_lines.append((e["source_node_uuid"], e["target_node_uuid"],
                               f"{sn} ─[{e.get('name','')}]→ {tn}: {e.get('fact','')}"))
        updated = 0
        batch_size = 10
        for start in range(0, len(nodes_with_edges), batch_size):
            batch = nodes_with_edges[start:start + batch_size]
            lines = []
            for uid, n in batch:
                related = [l for l in edge_lines if l[0] == uid or l[1] == uid]
                if not related:
                    continue
                lines.append(f"节点: {n['name']}（类别: {n.get('labels',[''])[2:] if len(n.get('labels',[]))>2 else 'unknown'}）")
                lines.append(f"当前简介: {n.get('summary', '') or '(无)'}")
                lines.append("关联关系:")
                for e in related[:30]:
                    lines.append(f"  {e[2]}")
                lines.append("")
            if not lines:
                continue
            prompt = (
                "你是凉宫春日系列图谱的摘要整理专家。\n"
                "以下是一个或多个图谱节点，每个节点有当前简介和所有关联关系。\n"
                "请为每个节点重新撰写简介，要求：\n"
                "1. 合并旧简介和关系中的新信息，去重\n"
                "2. 按重要度排序信息，不重要的（如一次性互动、琐碎提及）可以省略\n"
                "3. 保持简介有条理、易读\n"
                "4. 人物重点写性格/身份/关键事件，地点写作用/意义，物品写用途/归属\n\n"
                "直接输出JSON: {\"summaries\": [{\"node\":\"节点名\",\"summary\":\"整理后的简介\"}]}\n\n"
                + "\n".join(lines)
            )
            try:
                llm = self._get_llm()
                r = llm["client"].chat.completions.create(
                    model=llm["model"],
                    messages=[{"role": "system", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.1, max_tokens=4096)
                result = json.loads(r.choices[0].message.content)
                for item in result.get("summaries", []):
                    name = item.get("node", "")
                    summary = item.get("summary", "")
                    if not name or not summary:
                        continue
                    for uid, n in nodes_with_edges:
                        if n["name"] == name:
                            self.store.update_node_summary(uid, summary)
                            updated += 1
                            break
            except Exception as e:
                print(f"[builder] 全量整理失败(batch {start}): {e}")
                continue
        return updated
