"""SOS聊天室 - 后端服务"""

import asyncio
import json
import os
import random
import sys
import uuid

from pathlib import Path

import re

from dotenv import load_dotenv
# 从项目根目录加载 .env（override=True 覆盖被 ANSI 码污染的 shell 环境变量）
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# 清除 ANSI 转义码（防止终端粘贴导致模型名/URL 被污染）
_ANSI_CLEAN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _clean_env(key: str, default: str) -> str:
    return _ANSI_CLEAN.sub('', os.environ.get(key, default))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import File, UploadFile
from fastapi.staticfiles import StaticFiles

from config import CHARACTER_NAMES, load_persona, get_character_api_config
from engine.character import build_system_prompt, build_conversation_context
from engine.style import build_style_instruction
from database import (
    init_db, get_all_conversations, get_conversation, create_conversation,
    delete_conversation, update_conversation_scene,
    get_messages, add_message, batch_import_conversations,
    get_all_character_configs, get_character_config, upsert_character_config,
)
from tools.registry import load_tool_prompt, get_character_for_tool, get_tool_ids
from character_agent import CharacterAgent

app = FastAPI(title="SOS聊天室")

# ── 演示模式固定回复 ──

DEMO_RESPONSES = {
    "凉宫春日": [
        "啊——？你刚说什么？",
        "哼，你这人真没劲。",
        "哦？然后呢然后呢？说下去！",
        "切，无聊死了。",
        "决定了！就这么办！",
    ],
    "阿虚": [
        "……是是是，你说得都对。",
        "唉，我就知道会这样。",
        "喂喂，你认真的吗……算了。",
        "啊——（打哈欠）随你便吧。",
        "……我说什么都改变不了吧。",
    ],
    "长门有希": [
        "……（翻了一页书）",
        "……（目光没有离开书本）",
        "……正确。",
        "……可能性为87%。",
        "……计算完毕。",
    ],
    "朝比奈实玖瑠": [
        "啊，那个……",
        "对、对不起……",
        "是、是这样吗……？",
        "那个……我该怎么做呢……",
        "好、好的……",
    ],
    "古泉一树": [
        "嗯……这倒是有趣。",
        "呵呵，你注意到了啊。",
        "恐怕没那么简单——不过这只是我的推测。",
        "——开玩笑的。",
        "嗯，我赞同你的看法。",
    ],
}


def get_demo_response(character: str, user_message: str) -> str:
    replies = DEMO_RESPONSES.get(character, ["……"])
    return replies[sum(ord(c) for c in user_message) % len(replies)]


# ── LLM 回复清洗 ──

_SANITIZE_NAMES = sorted(CHARACTER_NAMES, key=len, reverse=True)
_LINE_WITH_NAME = re.compile(
    r'^\s*'
    rf'(?:【(?:{"|".join(re.escape(n) for n in _SANITIZE_NAMES)})】[：:]?\s*|'
    rf'(?:{"|".join(re.escape(n) for n in _SANITIZE_NAMES)})[：:]\s*|'
    r'【[^】]+】[：:]?\s*'
    r')'
)


def sanitize_llm_reply(text: str) -> str:
    """Strip character-name and bracket prefixes from each line of LLM output.

    如果整行以【角色名】开头，去掉前缀。如果整行就是【角色名】内容（替别人说话），删掉整行。
    """
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = _LINE_WITH_NAME.sub('', line).strip()
        if stripped:
            cleaned.append(stripped)
    return '\n'.join(cleaned).strip()


# ── 工具功能（动态加载自 tools/<id>/prompt.txt）──
# 无硬编码列表，新建工具只需在 tools/<id>/ 下加目录和 prompt.txt
_TOOLS = [{"id": tid.replace("-", "_"), "name": tid, "icon": "🔧", "desc": ""}
          for tid in get_tool_ids()]


# ── WebSocket 连接管理 ──

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self.active[client_id] = ws

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def broadcast(self, message: dict):
        dead = []
        for cid, ws in self.active.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.active.pop(cid, None)


manager = ConnectionManager()
sessions: dict[str, dict] = {}

# 全局默认配置
DEFAULT_API_KEY = _clean_env("ANTHROPIC_API_KEY", "")
DEFAULT_API_URL = _clean_env("ANTHROPIC_API_URL", "https://api.deepseek.com")
DEFAULT_MODEL = _clean_env("ANTHROPIC_MODEL", "deepseek-v4-flash")


def is_anthropic_api(api_url: str) -> bool:
    return "anthropic" in api_url.lower()


async def call_llm(api_key: str, api_url: str, model: str,
                   system_prompt: str, messages: list[dict]) -> str | None:
    """支持 Anthropic SDK 和 OpenAI SDK（DeepSeek等兼容），失败返回None。

    同步 SDK 调用跑在 to_thread 中，避免阻塞事件循环（否则 thinking 信号发不出去）。
    """
    if not api_key:
        return None

    try:
        if is_anthropic_api(api_url):
            def _call():
                import anthropic
                client = anthropic.Anthropic(api_key=api_key, base_url=api_url)
                resp = client.messages.create(
                    model=model, system=system_prompt, messages=messages,
                    max_tokens=2000, temperature=0.8,
                )
                return resp.content[0].text.strip()

            return await asyncio.to_thread(_call)
        else:
            def _call():
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=api_url, timeout=30)
                msgs = [{"role": "system", "content": system_prompt}] + messages
                resp = client.chat.completions.create(
                    model=model, messages=msgs,
                    max_tokens=2000, temperature=0.8,
                )
                return resp.choices[0].message.content.strip()

            return await asyncio.to_thread(_call)
    except Exception:
        return None  # caller负责fallback到demo


# ── 风格转化 ──

DEMO_PREFIXES = {
    "凉宫春日": lambda t: t.replace("。", "嘛！"),
    "阿虚": lambda t: t + "……唉。",
    "长门有希": lambda t: t,
    "朝比奈实玖瑠": lambda t: t.replace("。", "……吧？"),
    "古泉一树": lambda t: t + "——大概吧。",
}


async def style_transfer(api_key: str, api_url: str, model: str,
                         character: str, text: str) -> str:
    """Rewrite text in character's tone while preserving meaning exactly."""
    persona = load_persona(character)
    system = (
        f"Task: Rewrite the user's sentence as if {character} said it.\n"
        "IMPORTANT: This is a REWRITE task, not a conversation.\n"
        "1. Keep the exact same meaning and intent.\n"
        "2. Only change wording and tone to match the character's speaking style.\n"
        "3. NEVER respond to or reply to the sentence.\n"
        "4. NEVER add new content, opinions, suggestions, or narrative.\n"
        "5. Output ONLY the rewritten sentence, no prefixes or explanations.\n"
        "6. Preserve the full length — don't shorten.\n"
        "7. If the sentence is already in character, return it as-is.\n\n"
        f"Character reference:\n{persona[:1500]}"
    )

    if api_key:
        try:
            if is_anthropic_api(api_url):
                def _call():
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key, base_url=api_url)
                    return client.messages.create(
                        model=model, system=system,
                        messages=[{"role": "user", "content": text}],
                        max_tokens=2000, temperature=0.8, timeout=15,
                    ).content[0].text.strip()
                return await asyncio.to_thread(_call)
            else:
                def _call():
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url=api_url, timeout=15)
                    return client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system},
                                  {"role": "user", "content": text}],
                        max_tokens=2000, temperature=0.8,
                    ).choices[0].message.content.strip()
                return await asyncio.to_thread(_call)
        except Exception:
            pass

    fn = DEMO_PREFIXES.get(character, lambda t: t)
    return fn(text)


# ── 风格化质量检查 ──

_CHARACTER_MARKS = {
    "凉宫春日": ["！", "嘛", "呢", "啊——", "决定了", "有趣", "无聊", "给我", "哼"],
    "阿虚":     ["……", "唉", "是是是", "吐槽", "麻烦", "算了", "随你便", "哈？"],
    "长门有希": [],  # 长门无明确语气标记，走LLM判断
    "朝比奈实玖瑠": ["……", "对不起", "抱歉", "怎么办", "那个……", "吧？", "好、"],
    "古泉一树": ["——", "推测", "有趣", "大概", "恐怕", "呵呵", "开玩笑"],
}


def check_character_match(text: str, character: str) -> dict:
    """Check if text already sounds like the character.

    Returns dict with matched flag and score and message.
    """
    marks = _CHARACTER_MARKS.get(character, [])

    if not marks:
        # 无语气标记的角色（长门），长度短+无情绪词视为符合
        no_emote = not any(c in text for c in ["！", "？", "～", "嘛", "啦", "哟"])
        short = len(text) < 30
        if no_emote and short:
            return {"matched": True, "score": 0.8,
                    "message": f"✓ 很{character}的风格"}

    score = sum(1 for m in marks if m in text)
    ratio = score / max(len(marks), 1) / 2 + score / max(len(text), 1) * 2

    if ratio > 0.25:
        return {"matched": True, "score": min(ratio, 1.0),
                "message": f"✓ 很有{character}的味道，直接发吧！"}

    return {"matched": False, "score": round(ratio, 2), "message": f"角色匹配度: {round(ratio * 100)}%"}

# ── 上传目录 ──

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
_BG_PATH = UPLOAD_DIR / "background.jpg"


# ── API 路由 ──

@app.get("/api/characters")
async def get_characters():
    return {"characters": [{"name": n} for n in CHARACTER_NAMES]}


@app.get("/api/tools")
async def get_tools():
    return {"tools": _TOOLS}


# ── GraphRAG 构建 API ──

@app.post("/api/graphrag/build")
async def trigger_graph_build():
    """后台启动图谱构建，通过 status.json 报告进度。"""
    from graphrag.builder import GraphBuilder, read_status, _write_status
    from datetime import datetime

    current = read_status()
    if current.get("status") == "building":
        return {"success": False, "error": "构建正在进行中"}

    novels_dir = Path(__file__).resolve().parent.parent / "data" / "novels"
    txt_files = sorted(novels_dir.glob("*.txt"))
    if not txt_files:
        return {"success": False, "error": "未找到小说文件"}

    full_text = ""
    for f in txt_files:
        full_text += f"\n\n=== {f.stem} ===\n{f.read_text(encoding='utf-8')}"

    builder = GraphBuilder("haruhi_novel")
    # 清空旧数据，避免与上一轮构建混淆
    builder.store.clear_all()
    _write_status({"status":"building","progress":0,"message":"初始化...","nodes":0,"edges":0,
                   "total_chunks":0,"current_chunk":0,"started_at":str(datetime.now())})
    return {"success": True, "message": f"构建已启动，共 {len(full_text):,} 字符"}


@app.get("/api/graphrag/status")
async def get_graph_build_status():
    """获取构建进度。"""
    from graphrag.builder import read_status
    return read_status()


@app.get("/api/graphrag/data")
async def get_graph_data():
    """获取图谱统计和节点/边数据。"""
    try:
        from graphrag.store import GraphStore
        store = GraphStore("haruhi_novel")
        stats = store.get_statistics()
        if stats["total_nodes"] == 0:
            return {"success": True, "data": None, "message": "图谱为空，请先构建"}
        all_nodes = store.get_all_nodes()
        all_edges = store.get_all_edges()
        cat_count = {}
        node_map = {n["uuid"]: n for n in all_nodes}
        for n in all_nodes:
            labels = n.get("labels", [])
            cat = labels[2] if len(labels) > 2 else "unknown"
            cat_count[cat] = cat_count.get(cat, 0) + 1
        rel_count = {}
        for e in all_edges:
            name = e.get("name", "UNKNOWN")
            rel_count[name] = rel_count.get(name, 0) + 1

        # 取前 80 个节点 + 关联的边
        nodes_sample = all_nodes[:80]
        sample_uuids = {n["uuid"] for n in nodes_sample}
        edges_sample = [e for e in all_edges
                       if e["source_node_uuid"] in sample_uuids
                       and e["target_node_uuid"] in sample_uuids][:100]

        return {
            "success": True,
            "data": {
                "stats": stats,
                "by_category": cat_count,
                "by_type": rel_count,
                "by_relation": rel_count,
                "nodes_sample": [{
                    "name": n["name"],
                    "labels": n.get("labels", [])[1:],
                    "summary": n.get("summary", ""),
                    "uuid": n["uuid"]
                } for n in nodes_sample],
                "edges_sample": [{
                    "source_node_name": node_map.get(e["source_node_uuid"], {}).get("name", ""),
                    "target_node_name": node_map.get(e["target_node_uuid"], {}).get("name", ""),
                    "name": e.get("name", ""),
                    "source_node_uuid": e["source_node_uuid"],
                    "target_node_uuid": e["target_node_uuid"],
                } for e in edges_sample],
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/graphrag/clear")
async def clear_graph():
    """清零图谱数据。"""
    try:
        from graphrag.store import GraphStore
        from graphrag.builder import _write_status
        store = GraphStore("haruhi_novel")
        store.clear_all()
        _write_status({"status":"idle","progress":0,"message":"已清零","nodes":0,"edges":0})
        return {"success": True, "message": "图谱已清零"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 对话 REST API ──
    """Save API config to .env file on disk."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    if "api_key" in data and data["api_key"]:
        existing["ANTHROPIC_API_KEY"] = data["api_key"]
    if "api_url" in data and data["api_url"]:
        existing["ANTHROPIC_API_URL"] = data["api_url"]
    if "model" in data and data["model"]:
        existing["ANTHROPIC_MODEL"] = data["model"]

    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "ok"}


@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    """Save uploaded background image, return its URL."""
    content = await file.read()
    _BG_PATH.write_bytes(content)
    return {"url": "/uploads/background.jpg"}


@app.get("/api/background")
async def get_background():
    """Return the current background URL or empty."""
    if _BG_PATH.exists():
        return {"url": "/uploads/background.jpg"}
    return {"url": ""}


# ── 头像上传 ──

_AVATAR_DIR = UPLOAD_DIR / "avatars"
_AVATAR_DIR.mkdir(exist_ok=True)


@app.post("/api/upload-avatar/{character_name}")
async def upload_avatar(character_name: str, file: UploadFile = File(...)):
    """Save character avatar image, return its URL."""
    ext = Path(file.filename).suffix if file.filename else ".png"
    dest = _AVATAR_DIR / f"{character_name}{ext}"
    content = await file.read()
    dest.write_bytes(content)
    url = f"/uploads/avatars/{character_name}{ext}"
    # Update character config with avatar URL
    upsert_character_config(character_name, {"avatar": url})
    return {"url": url}


# ── 数据库初始化 ──

@app.on_event("startup")
def startup():
    init_db()


# ── 对话 REST API ──

@app.get("/api/conversations")
async def list_conversations():
    convs = get_all_conversations()
    return {"conversations": convs}


@app.post("/api/conversations")
async def new_conversation(data: dict):
    conv_id = data.get("id") or str(uuid.uuid4())
    character = data.get("character", "")
    conv_type = data.get("type", "single")
    title = data.get("title", "")
    scene_background = data.get("scene_background", "")
    absent_characters = json.dumps(data.get("absent_characters", []))
    player_character = data.get("player_character", "")
    create_conversation(conv_id, character, conv_type, title, scene_background, absent_characters, player_character)
    return {"id": conv_id}


@app.get("/api/conversations/{conv_id}")
async def get_conversation_detail(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        return {"error": "not found"}, 404
    messages = get_messages(conv_id)
    return {"conversation": conv, "messages": messages}


@app.delete("/api/conversations/{conv_id}")
async def remove_conversation(conv_id: str):
    delete_conversation(conv_id)
    return {"ok": True}


@app.patch("/api/conversations/{conv_id}/scene")
async def update_scene(conv_id: str, data: dict):
    scene_bg = data.get("scene_background")
    absent = data.get("absent_characters")
    if absent is not None:
        absent = json.dumps(absent)
    update_conversation_scene(conv_id, scene_bg, absent)
    return {"ok": True}


# ── 行动引擎 API ──


@app.post("/api/action-engine")
async def action_engine(data: dict):
    """春日行动引擎 LLM 调用。支持 plan(首次规划)、checkin(进度汇报)、add_tasks(追加任务)。"""
    prompt_type = data.get("type", "plan")
    user_input = data.get("input", "")
    if not user_input:
        return {"result": "你说啥？什么都没给我让我怎么安排！"}

    tool_prompt = load_tool_prompt("action-engine")
    persona_core = load_persona("凉宫春日")
    tool_dir = Path(__file__).resolve().parent.parent / "tools" / "action-engine"
    if prompt_type == "checkin":
        checkin_path = tool_dir / "checkin-prompt.txt"
        if checkin_path.exists():
            tool_prompt = checkin_path.read_text("utf-8").strip()
    elif prompt_type == "add_tasks":
        addtask_path = tool_dir / "addtask-prompt.txt"
        if addtask_path.exists():
            tool_prompt = addtask_path.read_text("utf-8").strip()

    full_prompt = persona_core + "\n\n" + tool_prompt if persona_core else tool_prompt

    reply = await call_llm(
        DEFAULT_API_KEY, DEFAULT_API_URL, DEFAULT_MODEL,
        full_prompt, [{"role": "user", "content": user_input}],
    )
    if reply is None:
        reply = "（分析失败，检查 API 配置后重试）"

    return {"result": reply}


@app.post("/api/conversations/batch-import")
async def batch_import(data: dict):
    convs = data.get("conversations", [])
    messages_map = data.get("messages", {})
    batch_import_conversations(convs, messages_map)
    return {"ok": True, "count": len(convs)}


# ── 角色配置 API ──


@app.get("/api/character-configs")
async def list_character_configs():
    configs = get_all_character_configs()
    return {"configs": configs}


@app.get("/api/character-configs/{name}")
async def get_single_character_config(name: str):
    config = get_character_config(name)
    if not config:
        return {"config": None}
    return {"config": config}


@app.put("/api/character-configs/{name}")
async def update_character_config(name: str, data: dict):
    upsert_character_config(name, data)
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = f"user_{random.randint(10000, 99999)}"
    await manager.connect(client_id, ws)

    sessions[client_id] = {
        "character": None,
        "partner": "",
        "message_log": [],
        "last_speaker": None,
        "api_key": DEFAULT_API_KEY,
        "api_url": DEFAULT_API_URL,
        "model": DEFAULT_MODEL,
        "character_api_config": {},
    }

    s = sessions[client_id]
    await ws.send_json({
        "type": "config",
        "demo_mode": not bool(s["api_key"]),
        "has_api_key": bool(s["api_key"]),
        "api_url": s["api_url"],
        "model": s["model"],
    })

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")
            session = sessions[client_id]

            # ── 设置配置（API Key / URL / 模型 / 角色独立配置） ──
            if msg_type == "set_config":
                if "api_key" in data:
                    session["api_key"] = (data["api_key"] or "").strip()
                if "api_url" in data:
                    session["api_url"] = (data["api_url"] or DEFAULT_API_URL).strip()
                if "model" in data:
                    session["model"] = (data["model"] or DEFAULT_MODEL).strip()
                if "character_config" in data:
                    session["character_api_config"] = data["character_config"]
                has = bool(session["api_key"])
                await ws.send_json({
                    "type": "config_updated",
                    "has_api_key": has,
                    "demo_mode": not has,
                    "api_url": session["api_url"],
                    "model": session["model"],
                })
                await manager.broadcast({
                    "type": "system",
                    "text": "API 配置已更新" if has else "已切换为演示模式",
                })

            # ── 选择角色 ──
            elif msg_type == "join":
                char = data.get("character", "")
                if char in CHARACTER_NAMES:
                    session["character"] = char
                    session["partner"] = data.get("partner", "")
                    session["conversation_id"] = data.get("conversation_id", "")
                    session["message_log"] = []
                    session["last_speaker"] = None

                    # 创建所有角色的独立 Agent（排除用户扮演的角色）
                    session["agents"] = {}
                    for name in CHARACTER_NAMES:
                        if name != char:  # 用户扮演的角色不需要 agent
                            session["agents"][name] = CharacterAgent(
                                name=name,
                                session=session,
                                call_llm_func=call_llm,
                                get_demo_func=get_demo_response,
                                sanitize_func=sanitize_llm_reply,
                                broadcast_func=lambda m: manager.broadcast(m),
                            )

                    if session.get("conversation_id"):
                        conv = get_conversation(session["conversation_id"])
                        if conv:
                            session["scene_background"] = conv.get("scene_background", "")
                            session["absent_characters"] = (
                                conv["absent_characters"]
                                if isinstance(conv.get("absent_characters"), list)
                                else []
                            )
                            # Restore message log from DB so LLM context is not empty after reconnect
                            db_messages = get_messages(session["conversation_id"])
                            session["message_log"] = [
                                {"character": m["role"], "text": m["content"], "is_bot": bool(m["is_bot"])}
                                for m in db_messages
                            ]
                            # Also restore each agent's independent message_log
                            for agent in session.get("agents", {}).values():
                                agent.restore_log(db_messages)
                    await ws.send_json({
                        "type": "character_ready",
                        "character": char,
                    })

            # ── 风格转化（旧，保留兼容）──
            elif msg_type == "style_transfer":
                char = session.get("character")
                text = data.get("text", "").strip()
                if not char or not text:
                    continue
                transformed = await style_transfer(
                    session["api_key"], session["api_url"], session["model"],
                    char, text,
                )
                await ws.send_json({
                    "type": "style_transferred",
                    "original": text,
                    "transformed": transformed,
                })

            # ── 风格化：Enter → 风格化 → 预览（新流程）──
            elif msg_type == "stylize":
                char = session.get("character")
                text = data.get("text", "").strip()
                if not char or not text:
                    continue

                # 先检查是否已有角色味
                quality = check_character_match(text, char)
                if quality["matched"]:
                    await ws.send_json({
                        "type": "stylized",
                        "original": text,
                        "transformed": None,
                        "already_in_character": True,
                        "message": quality["message"],
                        "score": quality.get("score", 0),
                    })
                else:
                    transformed = await style_transfer(
                        session["api_key"], session["api_url"], session["model"],
                        char, text,
                    )
                    await ws.send_json({
                        "type": "stylized",
                        "original": text,
                        "transformed": transformed,
                        "already_in_character": False,
                        "message": "✨ 已风格化",
                        "score": quality.get("score", 0),
                    })

            # ── 工具调用（结果只在调用者的连接中显示）──
            elif msg_type == "tool_invoke":
                tool_id = data.get("tool_id", "")
                content = data.get("content", "").strip()
                if not tool_id or not content:
                    continue

                prompt = load_tool_prompt(tool_id)
                if not prompt:
                    await ws.send_json({
                        "type": "error",
                        "text": f"未找到工具：{tool_id}",
                    })
                    continue

                # 动态加载角色 Personality Core 作为上下文
                char = get_character_for_tool(tool_id)
                if char:
                    persona_core = load_persona(char)
                    full_prompt = persona_core + "\n\n" + prompt
                else:
                    full_prompt = prompt

                reply = await call_llm(
                    session["api_key"], session["api_url"], session["model"],
                    full_prompt, [{"role": "user", "content": content}],
                )
                if reply is None:
                    reply = "（工具调用失败，请检查 API 配置后重试）"
                else:
                    reply = sanitize_llm_reply(reply)

                await ws.send_json({
                    "type": "tool_result",
                    "tool_id": tool_id,
                    "result": reply,
                })

            # ── 发送消息 ──
            elif msg_type == "message":
                user_char = session.get("character")
                if not user_char:
                    await ws.send_json({
                        "type": "error",
                        "text": "请先在左侧选择角色",
                    })
                    continue

                text = data.get("text", "").strip()
                if not text:
                    continue

                # 记录并广播用户消息
                user_msg = {"character": user_char, "text": text, "is_bot": False}
                session["message_log"].append(user_msg)
                session["last_speaker"] = user_char
                await manager.broadcast({
                    "type": "message",
                    "character": user_char,
                    "text": text,
                    "is_bot": False,
                })

                # 持久化用户消息
                if session.get("conversation_id"):
                    add_message(session["conversation_id"], user_char, text, is_bot=0)

                # ── 准备 Agent ──
                agents = session.get("agents", {})
                if not agents:
                    continue

                absent = session.get("absent_characters", [])
                active_agents = {
                    name: agent for name, agent in agents.items()
                    if name not in absent
                }

                partner = session.get("partner", "")
                if partner in CHARACTER_NAMES and partner in active_agents:
                    active_agents = {partner: active_agents[partner]}

                if not active_agents:
                    continue

                from engine.trigger import get_character_probs
                novel_probs = get_character_probs(session.get("last_speaker"))
                user_msg_obj = {"character": session["character"], "text": text, "is_bot": False}

                # ── Round 1：所有 agent 回复用户消息 ──
                coros = [
                    agent.observe_and_reply(user_msg_obj, novel_probs)
                    for agent in active_agents.values()
                ]
                round1 = await asyncio.gather(*coros, return_exceptions=True)

                # 处理 Round 1 回复
                round1_replies = []
                agent_names = list(active_agents.keys())
                for i, result in enumerate(round1):
                    agent_name = agent_names[i]
                    if isinstance(result, Exception):
                        print(f"[agent] {agent_name} error: {result}")
                        continue
                    if result is None:
                        continue

                    round1_replies.append(result)
                    await manager.broadcast(result)
                    if session.get("conversation_id"):
                        add_message(session["conversation_id"], agent_name, result["text"], is_bot=1)

                # ── Round 2：agent 之间互相反应 ──
                if round1_replies:
                    round2_replies = []
                    # 每条 Round 1 回复，发给所有 agent 观察
                    for reply in round1_replies:
                        reply_msg = {
                            "character": reply["character"],
                            "text": reply["text"],
                            "is_bot": True,
                        }
                        sub_coros = [
                            agent.observe_and_reply(reply_msg, novel_probs)
                            for agent in active_agents.values()
                        ]
                        sub_results = await asyncio.gather(*sub_coros, return_exceptions=True)

                        for sr in sub_results:
                            if sr is not None and not isinstance(sr, Exception):
                                round2_replies.append(sr)

                    # Round 2 广播 + 持久化
                    for result in round2_replies:
                        await manager.broadcast(result)
                        if session.get("conversation_id"):
                            add_message(session["conversation_id"], result["character"], result["text"], is_bot=1)

                # ── 兜底：无人回复 ──
                if not round1_replies and active_agents:
                    top_agent = max(
                        active_agents.values(),
                        key=lambda a: novel_probs.get(a.name, 0)
                    )
                    forced_reply = await top_agent._generate_reply(user_msg_obj)
                    if forced_reply:
                        await manager.broadcast(forced_reply)
                        if session.get("conversation_id"):
                            add_message(session["conversation_id"], top_agent.name, forced_reply["text"], is_bot=1)

            # ── 更新场景设置 ──
            elif msg_type == "update_scene":
                bg = data.get("scene_background", "")
                absent = data.get("absent_characters", [])
                session["scene_background"] = bg
                session["absent_characters"] = absent
                if session.get("conversation_id"):
                    update_conversation_scene(
                        session["conversation_id"],
                        scene_background=bg,
                        absent_characters=json.dumps(absent),
                    )
                await ws.send_json({
                    "type": "scene_updated",
                    "ok": True,
                })

            # ── 清除对话 ──
            elif msg_type == "clear":
                session["message_log"] = []
                session["last_speaker"] = None
                await ws.send_json({"type": "system", "text": "对话已清除"})

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        char = sessions.get(client_id, {}).get("character", "某人")
        await manager.broadcast({"type": "system", "text": f"{char} 离开了聊天室"})


# ── 静态文件 ──

# 图谱构建页面
GRAPH_BUILD_HTML = Path(__file__).resolve().parent / "graphrag_build.html"


@app.get("/build-graph")
async def graphrag_page():
    """Serve the graphrag build frontend."""
    if GRAPH_BUILD_HTML.exists():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(GRAPH_BUILD_HTML.read_text(encoding="utf-8"))
    return {"error": "page not found"}


# Serve uploaded files (background images etc.)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Try dist (built React app) first, fall back to frontend/ (old single-page)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
elif FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ── 启动 ──

def find_free_port(start: int = 8000, max_attempts: int = 10) -> int:
    import socket
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start


def free_port(port: int):
    """Kill any process using the given port (Windows)."""
    import subprocess, time
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port} | findstr LISTENING',
            shell=True, capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    subprocess.run(['taskkill', '/f', '/pid', pid],
                                   capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(0.5)


if __name__ == "__main__":
    import uvicorn

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    free_port(8000)
    port = find_free_port(8000)
    if port != 8000:
        print(f"[SOS] 端口8000被占用，改用 {port}")

    # 自动打开浏览器
    import webbrowser
    webbrowser.open(f"http://localhost:{port}")

    print(f"[SOS] 启动完成")
    print(f"  前端地址: http://localhost:{port}")
    if DEFAULT_API_KEY:
        print(f"  状态: 已配置API Key（AI模式）")
    else:
        print(f"  状态: 演示模式（请在页面右上角设置API Key）")
    print()

    uvicorn.run("main:app", host="0.0.0.0", port=port)
