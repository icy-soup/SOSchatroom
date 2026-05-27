"""SOS聊天室 - 后端服务"""

import asyncio
import json
import os
import random
import sys

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

from config import CHARACTER_NAMES, load_character_skill, get_character_api_config
from engine.trigger import select_responders
from engine.character import build_system_prompt, build_conversation_context
from engine.style import build_style_instruction

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
_SANITIZE_PATTERN = re.compile(
    r'^(?:'
    rf'【(?:{"|".join(re.escape(n) for n in _SANITIZE_NAMES)})】[：:]?\s*|'
    rf'(?:{"|".join(re.escape(n) for n in _SANITIZE_NAMES)})[：:]\s*|'
    r'【[^】]+】[：:]?\s*|'
    r'[—\-]\s*'
    r')'
)


def sanitize_llm_reply(text: str) -> str:
    """Strip character-name and bracket prefixes from LLM output."""
    return _SANITIZE_PATTERN.sub('', text).strip()


# ── 工具功能 ──

_TOOLS = [
    {"id": "boredom_checker", "name": "反无聊审查器", "icon": "🔍",
     "desc": "分析待办清单，区分真该做的事和你在拖的事"},
    {"id": "intuition_booster", "name": "直觉加速器", "icon": "⚡",
     "desc": "给你一个直觉判断和行动方案，不用再纠结"},
    {"id": "action_tester", "name": "行动力测试", "icon": "💪",
     "desc": "给你的计划打分，看看春日来做要多久"},
]

# 加载春日 SKILL.md 作为工具的角色参考
_HARUHI_SKILL = load_character_skill("凉宫春日")

_TOOL_PROMPTS = {
    "boredom_checker": _HARUHI_SKILL + """

你现在是凉宫春日——SOS团团长。用你的风格分析这份待办清单。

任务：
1. 区分「真无聊但必须做」的事和「用户单纯在拖延」的事
2. 每项加简短理由
3. 给一个春日的行动建议

记住：你就是凉宫春日本人。用「我」第一人称说话，用感叹号，直接下判断。

输出格式：
🔥 真无聊但必须做的：
- XXX：理由

💤 你在拖延的：
- XXX：真相

💡 我的建议：XXX""",

    "intuition_booster": _HARUHI_SKILL + """

你现在是凉宫春日——SOS团团长。用你的风格帮用户做决定。

任务：
1. 直觉判断（3秒内给出答案）
2. 行动方案（3步以内）
3. 可选理性分析

记住：你就是凉宫春日本人。用「我」第一人称说话，直觉判断要干脆。

输出格式：
我的直觉：XXX

行动方案：
1. XXX
2. XXX
3. XXX""",

    "action_tester": _HARUHI_SKILL + """

你现在是凉宫春日——SOS团团长。用你的风格评估这个计划。

任务：
1. 行动力评分 1-10
2. 我（春日）来做预计要多久
3. 分析为什么你做不到
4. 给春日的建议

记住：你就是凉宫春日本人。用「我」第一人称说话，评分要干脆直接。

输出格式：
行动力评分：X/10

我来做的话预计：XXX

为什么你做不到：
- XXX
- XXX

我的建议：XXX""",
}


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
    skill_text = load_character_skill(character)
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
        f"Character reference:\n{skill_text[:1500]}"
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


@app.post("/api/save-config")
async def save_config(data: dict):
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


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = f"user_{random.randint(10000, 99999)}"
    await manager.connect(client_id, ws)

    sessions[client_id] = {
        "character": None,
        "partner": "",
        "history": [],
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
                    session["history"] = []
                    session["last_speaker"] = None
                    await manager.broadcast({
                        "type": "system",
                        "text": f"{char} 加入了聊天室",
                    })
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
                prompt = _TOOL_PROMPTS.get(tool_id)
                if not tool_id or not content or not prompt:
                    continue

                reply = await call_llm(
                    session["api_key"], session["api_url"], session["model"],
                    prompt, [{"role": "user", "content": content}],
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
                session["history"].append(user_msg)
                session["last_speaker"] = user_char
                await manager.broadcast({
                    "type": "message",
                    "character": user_char,
                    "text": text,
                    "is_bot": False,
                })

                # 选择自动回复角色（已按概率降序排列）
                existing = set()
                responders = select_responders(
                    last_speaker=session.get("last_speaker"),
                    message_text=text,
                    user_character=user_char,
                    existing_responders=existing,
                    conversation_history=session.get("history", []),
                )

                # 按对话对象过滤（单人聊天只让指定角色回复，群聊不过滤）
                partner = session.get("partner", "")
                if partner in CHARACTER_NAMES:
                    responders = [r for r in responders if r == partner]
                    if not responders:
                        responders = [partner]

                # 串行回复：每个响应者依次思考、回复，
                # 先回复的人的输出作为后面回复者的语料
                for responder in responders:
                    existing.add(responder)

                    # 1. 广播思考中提示
                    await manager.broadcast({
                        "type": "thinking",
                        "character": responder,
                    })

                    style_instruction = build_style_instruction(responder, user_char)
                    system_prompt = build_system_prompt(responder)
                    if style_instruction:
                        system_prompt += f"\n\n{style_instruction}"

                    # 2. 构建 context —— 角色信息嵌入在每条消息 content 中
                    ctx = build_conversation_context(session["history"])
                    ctx.append({
                        "role": "user",
                        "content": f"【{user_char}】{text}",
                    })

                    # 检查角色独立API配置（优先级：会话独立配置 > 文件配置 > 全局默认）
                    char_api = get_character_api_config(responder)
                    session_char = session.get("character_api_config", {}).get(responder, {})
                    char_api_url = (session_char.get("api_url")
                                    or char_api.get("api_url")
                                    or session["api_url"])
                    char_model = (session_char.get("model")
                                  or char_api.get("model")
                                  or session["model"])

                    reply = await call_llm(
                        session["api_key"], char_api_url, char_model,
                        system_prompt, ctx,
                    )
                    if reply is None:
                        await manager.broadcast({
                            "type": "system",
                            "text": f"AI 回复失败（{responder}），已切换为演示模式回复",
                        })
                        reply = get_demo_response(responder, text)
                    else:
                        reply = sanitize_llm_reply(reply)

                    # 3. 清除思考中
                    await manager.broadcast({
                        "type": "thinking_clear",
                        "character": responder,
                    })

                    # 4. 追加到历史（后续响应者能看到这条回复）
                    bot_msg = {"character": responder, "text": reply, "is_bot": True}
                    session["history"].append(bot_msg)
                    session["last_speaker"] = responder

                    # 5. 广播最终回复
                    await manager.broadcast({
                        "type": "message",
                        "character": responder,
                        "text": reply,
                        "is_bot": True,
                    })

            # ── 清除对话 ──
            elif msg_type == "clear":
                session["history"] = []
                session["last_speaker"] = None
                await ws.send_json({"type": "system", "text": "对话已清除"})

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        char = sessions.get(client_id, {}).get("character", "某人")
        await manager.broadcast({"type": "system", "text": f"{char} 离开了聊天室"})


# ── 静态文件 ──

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
