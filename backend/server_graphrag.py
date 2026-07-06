"""独立的图谱构建服务器（端口 8001），不干扰主聊天室（8000）。"""
import sys, os, json, glob
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="GraphRAG Builder")

# CORS — 允许前端独立调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载 HTML
HTML_PATH = Path(__file__).parent / "templates" / "graphrag_build.html"
HTML_CONTENT = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else "<h1>未找到页面</h1>"

# 导入 graphrag
from graphrag.builder import GraphBuilder, read_status, _write_status
from graphrag.store import GraphStore, GRAPH_DATA_DIR

# 启动时同步 DB 状态（服务器重启后线程已死）
db_files = glob.glob(os.path.join(GRAPH_DATA_DIR, "*.db"))
for fp in db_files:
    gid = os.path.splitext(os.path.basename(fp))[0]
    if gid.endswith("-wal") or gid.endswith("-shm"):
        continue
    _store = GraphStore(gid)
    _stats = _store.get_statistics()
    _current = read_status(gid)
    if _current.get("status") in ("building", "paused"):
        _write_status(gid, {**_current, "stale": True, "nodes": _stats["total_nodes"], "edges": _stats["total_edges"]})
        print(f"[server] stale 构建 (graph_id={gid}, status={_current['status']})")
    elif _stats["total_nodes"] > 0:
        _write_status(gid, {"status": "completed", "progress": 1.0,
                           "nodes": _stats["total_nodes"], "edges": _stats["total_edges"],
                           "message": "图谱就绪"})
    else:
        _write_status(gid, {"status": "idle", "progress": 0, "nodes": 0, "edges": 0, "message": "空图谱"})

# 数据源
NOVELS_DIR = Path(__file__).resolve().parent.parent / "data" / "novels"
DEFAULT_FILE = NOVELS_DIR / "txt全卷.txt"
_current_source = "default"


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.get("/api/graphrag/default-file")
async def default_file_info():
    """返回默认小说文件信息。"""
    if DEFAULT_FILE.exists():
        return {"success": True, "filename": "txt全卷.txt", "size_mb": DEFAULT_FILE.stat().st_size / 1048576}
    return {"success": False, "error": "默认文件不存在"}


@app.post("/api/graphrag/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传自定义小说文本文件。"""
    global _current_source
    if not file.filename.endswith('.txt'):
        return {"success": False, "error": "仅支持 .txt 文件"}
    dest = NOVELS_DIR / file.filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    _current_source = file.filename
    return {"success": True, "filename": file.filename, "size": len(content)}


# ─── 图谱管理 ────────────────────────────────────────────────────

@app.get("/api/graphrag/graphs")
async def list_graphs():
    """列出 data/graphs/ 下所有 .db 文件，返回元信息。"""
    files = sorted(glob.glob(os.path.join(GRAPH_DATA_DIR, "*.db")))
    graphs = []
    for fp in files:
        gid = os.path.splitext(os.path.basename(fp))[0]
        store = GraphStore(gid)
        stats = store.get_statistics()
        size_mb = os.path.getsize(fp) / 1048576
        graphs.append({
            "graph_id": gid,
            "display_name": gid,
            "nodes": stats["total_nodes"],
            "edges": stats["total_edges"],
            "size_mb": round(size_mb, 2),
            "has_data": stats["total_nodes"] > 0,
        })
    return {"success": True, "graphs": graphs}


from datetime import datetime

@app.post("/api/graphrag/backup")
async def backup_graph(graph_id: str = Query(..., description="要备份的图谱 ID")):
    """安全另存为当前图谱（SQLite backup API）。"""
    store = GraphStore(graph_id)
    stats = store.get_statistics()
    if stats["total_nodes"] == 0:
        return {"success": False, "error": "当前图谱为空，无需备份"}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_id = f"{graph_id}_{timestamp}"
    store.backup(new_id)
    new_store = GraphStore(new_id)
    new_stats = new_store.get_statistics()
    return {
        "success": True,
        "graph_id": new_id,
        "display_name": new_id,
        "nodes": new_stats["total_nodes"],
        "edges": new_stats["total_edges"],
        "size_mb": round(os.path.getsize(new_store._db_path) / 1048576, 2),
    }


@app.post("/api/graphrag/hide")
async def toggle_hide_node(
    graph_id: str = Query(..., description="图谱 ID"),
    node_uuid: str = Query(..., description="节点 UUID"),
    hidden: bool = Query(True, description="true=隐藏, false=恢复"),
):
    """持久化节点隐藏状态到 DB。"""
    store = GraphStore(graph_id)
    settings = store.get_settings()
    hidden_nodes = settings.get("hidden_nodes", [])
    if hidden:
        if node_uuid not in hidden_nodes:
            hidden_nodes.append(node_uuid)
    else:
        hidden_nodes = [u for u in hidden_nodes if u != node_uuid]
    store.update_settings({"hidden_nodes": hidden_nodes})
    return {"success": True, "settings": {"hidden_nodes": hidden_nodes}}


# ─── 主页 ────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return HTMLResponse(HTML_CONTENT)


# ─── 构建 ────────────────────────────────────────────────────────

@app.post("/api/graphrag/build")
async def build(graph_id: str = Query("haruhi_novel", description="要构建的图谱 ID")):
    from datetime import datetime
    current = read_status(graph_id)
    if current.get("status") == "building":
        return {"success": False, "error": "构建正在进行中"}

    # 检查是否有其他图正在构建
    full = read_status()
    active = full.get("active_graph_id")
    if active and active != graph_id:
        return {"success": False, "error": f"另一个图谱「{active}」正在构建中"}

    # 确定数据源
    if _current_source == "default":
        target = DEFAULT_FILE
        label = "txt全卷.txt"
    else:
        target = NOVELS_DIR / _current_source
        label = _current_source

    if not target.exists():
        return {"success": False, "error": f"文件不存在: {label}"}

    full_text = target.read_text(encoding="utf-8")
    builder = GraphBuilder(graph_id)
    builder.store.clear_all()
    _write_status(graph_id, {"status": "building", "progress": 0, "message": "初始化...",
                             "nodes": 0, "edges": 0, "total_chunks": 0, "current_chunk": 0,
                             "started_at": str(datetime.now())})
    builder.build_async(full_text)
    return {"success": True, "message": f"构建已启动 · {label} · {len(full_text):,} 字符"}


@app.get("/api/graphrag/status")
async def status(graph_id: str = Query(None, description="图谱 ID（不传则返回完整状态）")):
    return read_status(graph_id)


@app.post("/api/graphrag/pause")
async def pause_build():
    full = read_status()
    active = full.get("active_graph_id")
    if not active:
        return {"success": False, "error": "没有正在进行的构建"}
    current = full["graphs"].get(active, {})
    if current.get("status") != "building":
        return {"success": False, "error": "没有正在进行的构建"}
    _write_status(active, {**current, "status": "paused", "message": "已暂停"})
    print(f"[server] 构建已暂停 (graph_id={active})")
    return {"success": True, "message": "构建已暂停", "graph_id": active}


@app.post("/api/graphrag/resume")
async def resume_build():
    full = read_status()
    active = full.get("active_graph_id")
    if not active:
        return {"success": False, "error": "没有暂停的构建"}
    current = full["graphs"].get(active, {})
    if current.get("status") != "paused":
        return {"success": False, "error": "没有暂停的构建"}

    if current.get("stale"):
        skip = current.get("current_chunk", 0)
        target = DEFAULT_FILE if _current_source == "default" else NOVELS_DIR / _current_source
        if not target.exists():
            return {"success": False, "error": "数据文件不存在"}
        full_text = target.read_text(encoding="utf-8")
        builder = GraphBuilder(active)
        builder.build_async(full_text, skip_chunks=skip)
        _write_status(active, {**current, "stale": False, "status": "building",
                               "message": f"继续构建中（跳过 {skip} 块）..."})
        print(f"[server] 跨重启继续构建 (graph_id={active}), 跳过 {skip} 块")
    else:
        _write_status(active, {**current, "status": "building", "message": "继续构建中..."})
        print(f"[server] 构建已继续 (graph_id={active})")
    return {"success": True, "message": "构建已继续"}


@app.post("/api/graphrag/clear")
async def clear(graph_id: str = Query("haruhi_novel", description="图谱 ID")):
    store = GraphStore(graph_id)
    store.clear_all()
    _write_status(graph_id, {"status": "idle", "progress": 0, "message": "已清零", "nodes": 0, "edges": 0})
    return {"success": True, "message": "图谱已清零"}


# ─── 数据 ────────────────────────────────────────────────────────

@app.get("/api/graphrag/data")
async def data(graph_id: str = Query("haruhi_novel", description="图谱 ID"), limit: int = 1000):
    try:
        store = GraphStore(graph_id)
        stats = store.get_statistics()
        settings = store.get_settings()
        if stats["total_nodes"] == 0:
            return {"success": True, "data": {"settings": settings, "stats": stats}, "message": "图谱为空"}
        all_nodes = store.get_all_nodes()
        all_edges = store.get_all_edges()
        node_map = {n["uuid"]: n for n in all_nodes}
        cat_count = {}
        type_count = {}
        for n in all_nodes:
            labels = n.get("labels", [])
            cat = labels[2] if len(labels) > 2 else "unknown"
            cat_count[cat] = cat_count.get(cat, 0) + 1
            etype = labels[1] if len(labels) > 1 else "Unknown"
            type_count[etype] = type_count.get(etype, 0) + 1
        rel_count = {}
        for e in all_edges:
            name = e.get("name", "UNKNOWN")
            rel_count[name] = rel_count.get(name, 0) + 1

        from collections import Counter
        degree = Counter()
        for e in all_edges:
            degree[e["source_node_uuid"]] += 1
            degree[e["target_node_uuid"]] += 1

        # 按度数排序，取关联最多的前 N 个节点
        sorted_by_degree = sorted(all_nodes, key=lambda n: degree.get(n["uuid"], 0), reverse=True)
        nodes_sample = sorted_by_degree[:limit]
        sample_uuids = {n["uuid"] for n in nodes_sample}
        edges_sample = [e for e in all_edges
                       if e["source_node_uuid"] in sample_uuids
                       and e["target_node_uuid"] in sample_uuids]

        # 最高度节点
        display_degree = {uid: sum(1 for e in edges_sample if e["source_node_uuid"]==uid or e["target_node_uuid"]==uid) for uid in sample_uuids}
        max_deg_uuid = max(display_degree, key=display_degree.get) if display_degree else None
        max_deg_node = node_map.get(max_deg_uuid, {}).get("name", "") if max_deg_uuid else ""
        max_deg_count = display_degree.get(max_deg_uuid, 0) if max_deg_uuid else 0

        return {
            "success": True,
            "data": {
                "settings": settings,
                "stats": stats,
                "displayed_nodes": len(nodes_sample),
                "displayed_edges": len(edges_sample),
                "max_degree": {"node": max_deg_node, "count": max_deg_count},
                "by_category": cat_count, "by_type": type_count, "by_relation": rel_count,
                "nodes_sample": [{"name": n["name"], "labels": n.get("labels", [])[1:],
                                  "summary": n.get("summary", ""), "uuid": n["uuid"]} for n in nodes_sample],
                "edges_sample": [{
                    "source_node_name": node_map.get(e["source_node_uuid"], {}).get("name", ""),
                    "target_node_name": node_map.get(e["target_node_uuid"], {}).get("name", ""),
                    "name": e.get("name", ""),
                    "fact": e.get("fact", ""),
                    "uuid": e.get("uuid", ""),
                    "source_node_uuid": e["source_node_uuid"],
                    "target_node_uuid": e["target_node_uuid"],
                } for e in edges_sample],
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 编辑 ────────────────────────────────────────────────────────

@app.post("/api/graphrag/edge/add")
async def add_edge(
    graph_id: str = Query("haruhi_novel", description="图谱 ID"),
    source_uuid: str = Query(""), target_uuid: str = Query(""),
    name: str = Query("认识"), fact: str = Query(""),
):
    if not source_uuid or not target_uuid:
        return {"success": False, "error": "需要 source_uuid 和 target_uuid"}
    store = GraphStore(graph_id)
    src = store.get_node(source_uuid)
    tgt = store.get_node(target_uuid)
    if not src or not tgt:
        return {"success": False, "error": "节点不存在"}
    import uuid
    edge_uuid = uuid.uuid4().hex
    now = datetime.now().isoformat()
    store._execute("INSERT INTO edges (uuid, graph_id, name, fact, source_node_uuid, target_node_uuid, created_at) VALUES (?,?,?,?,?,?,?)",
                   (edge_uuid, graph_id, name, fact[:200], source_uuid, target_uuid, now))
    return {"success": True, "message": f"已添加: {src['name']} →{name}→ {tgt['name']}", "uuid": edge_uuid}


@app.post("/api/graphrag/edge/delete")
async def delete_edge(uuid: str = Query(""), graph_id: str = Query("haruhi_novel", description="图谱 ID")):
    if not uuid:
        return {"success": False, "error": "需要边 uuid"}
    store = GraphStore(graph_id)
    store._execute("DELETE FROM edges WHERE uuid = ? AND graph_id = ?", (uuid, graph_id))
    return {"success": True, "message": "边已删除"}


@app.post("/api/graphrag/node/merge")
async def merge_nodes(
    source_uuid: str = Query(""), target_uuid: str = Query(""),
    graph_id: str = Query("haruhi_novel", description="图谱 ID"),
):
    if not source_uuid or not target_uuid:
        return {"success": False, "error": "需要 source_uuid 和 target_uuid"}
    if source_uuid == target_uuid:
        return {"success": False, "error": "不能合并到自身"}
    store = GraphStore(graph_id)
    src = store.get_node(source_uuid)
    tgt = store.get_node(target_uuid)
    if not src or not tgt:
        return {"success": False, "error": "节点不存在"}

    all_nodes = {n["uuid"]: n for n in store.get_all_nodes()}
    all_edges = store.get_all_edges()
    def node_edges(uuid):
        related = []
        for e in all_edges:
            sn = all_nodes.get(e["source_node_uuid"], {}).get("name", "?")
            tn = all_nodes.get(e["target_node_uuid"], {}).get("name", "?")
            if e["source_node_uuid"] == uuid:
                related.append(f"  →{e.get('name','')}→ {tn}: {e.get('fact','')}")
            elif e["target_node_uuid"] == uuid:
                related.append(f"  {sn} →{e.get('name','')}→ ")
        return related

    info = f"""节点A: {src['name']}
类型: {src.get('labels', [])}
简介: {src.get('summary', '')}
关联关系:
{chr(10).join(node_edges(source_uuid))}

节点B: {tgt['name']}
类型: {tgt.get('labels', [])}
简介: {tgt.get('summary', '')}
关联关系:
{chr(10).join(node_edges(target_uuid))}"""

    prompt = f"你是凉宫春日系列图谱的实体合并专家。判断以下两个节点是否为同一实体。\n{info}\n如果是同一实体，输出规范名称和合并后的简介。\n输出JSON: {{\"should_merge\":true/false,\"canonical_name\":\"规范名\",\"summary\":\"合并后的简介\",\"reason\":\"判断理由(一句话)\"}}"
    try:
        builder = GraphBuilder(graph_id)
        llm = builder._get_llm()
        r = llm["client"].chat.completions.create(
            model=llm["model"],
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0.1, max_tokens=1024)
        result = json.loads(r.choices[0].message.content)
    except Exception as e:
        return {"success": False, "error": f"LLM 判断失败: {e}"}

    if not result.get("should_merge"):
        return {"success": False, "error": f"LLM 判断不是同一实体: {result.get('reason','')}", "llm_result": result}

    name = result.get("canonical_name", tgt["name"])
    summary = result.get("summary", tgt.get("summary", ""))
    ok = store.merge_nodes(source_uuid, target_uuid)
    if ok:
        store.update_node_name(target_uuid, name)
        store.update_node_summary(target_uuid, summary)
        print(f"[server] LLM合并: {src['name']}({src.get('uuid','')[:8]}) → {name}({target_uuid[:8]})")
        return {"success": True, "message": f"已合并: {src['name']} → {name}", "reason": result.get("reason","")}
    return {"success": False, "error": "合并失败"}


@app.post("/api/graphrag/shutdown")
async def shutdown():
    """关闭后端服务器。"""
    print("[server] 收到关闭指令，服务器即将停止")
    import threading
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"success": True, "message": "服务器正在关闭"}


if __name__ == "__main__":
    print("[graphrag] 独立服务器启动在 http://localhost:8001")
    print("[graphrag] 访问 http://localhost:8001 打开图谱构建页面")
    uvicorn.run(app, host="0.0.0.0", port=8001)
