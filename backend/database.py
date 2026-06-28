"""SOS团聊天室 - SQLite 数据库层

Schema + CRUD for conversations, messages, and character_configs.

用法:
    from database import init_db, get_all_conversations, add_message, ...

    init_db()  # 应用启动时调用一次
    conv = create_conversation("conv_001", "凉宫春日")
    msg = add_message("conv_001", "凉宫春日", "大家好！", is_bot=0)
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── DB 路径（相对于本文件） ──

_DB_DIR = Path(__file__).resolve().parent
_DB_PATH = _DB_DIR / "chatroom.db"

# ── 预览截断长度 ──

_MAX_PREVIEW_LENGTH = 100

# ── 角色配置允许字段 ──

_ALLOWED_CONFIG_FIELDS: frozenset[str] = frozenset({
    "display_name",
    "avatar",
    "signature",
    "temperature",
    "reply_length",
    "tone",
    "custom_instructions",
    "title",
    "description",
    "api_url",
    "model",
    "api_key",
})


# ===================================================================
#  连接管理
# ===================================================================

def get_connection() -> sqlite3.Connection:
    """返回 SQLite 连接。

    特性:
        - WAL 模式（并发读友好）
        - row_factory = sqlite3.Row（按列名访问）
        - 外键约束开启
    """
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    """返回当前 UTC 时间的 ISO 8601 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _parse_json_field(val: Any) -> Any:
    """尝试将值解析为 JSON；失败则原样返回。"""
    if isinstance(val, str) and val.strip():
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _ensure_json_array(val: Any) -> str:
    """确保值以 JSON 数组字符串形式返回。

    接受 str（原样返回）、list（dump）、None（返回默认 '[]'）。
    """
    if val is None:
        return "[]"
    if isinstance(val, str):
        return val if val.strip() else "[]"
    # list / tuple / set 等
    return json.dumps(val, ensure_ascii=False)


def _row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转为普通 dict，并自动解析 JSON 字段。"""
    d = dict(row)
    # 解析 absent_characters 字段（JSON 数组字符串 -> list）
    if "absent_characters" in d:
        d["absent_characters"] = _parse_json_field(d["absent_characters"])
        if not isinstance(d["absent_characters"], list):
            d["absent_characters"] = []
    return d


def _dict_to_message_row(d: dict) -> dict:
    """**kwargs-safe helper 将原始 dict 转成 messages 表插入可用的 dict。"""
    return {
        "conversation_id": d.get("conversation_id", ""),
        "role": d.get("role", d.get("character", "")),
        "content": d.get("content", d.get("text", "")),
        "is_bot": int(d.get("is_bot", d.get("isBot", 0))),
        "created_at": d.get("created_at", _now()),
    }


# ===================================================================
#  初始化
# ===================================================================

def init_db() -> None:
    """创建表（IF NOT EXISTS）。

    conversations:
        id                TEXT PK
        character         TEXT NOT NULL       — 对话关联的主要角色
        type              TEXT DEFAULT 'single' — 'single' | 'group'
        title             TEXT DEFAULT ''
        scene_background  TEXT DEFAULT ''
        absent_characters TEXT DEFAULT '[]'   — JSON 数组
        created_at        TEXT NOT NULL
        updated_at        TEXT NOT NULL
        message_count     INTEGER DEFAULT 0
        preview           TEXT DEFAULT ''

    messages:
        id                INTEGER PK AUTOINCREMENT
        conversation_id   TEXT NOT NULL       — FK -> conversations(id)
        role              TEXT NOT NULL       — 角色名 / 'user'
        content           TEXT NOT NULL
        is_bot            INTEGER DEFAULT 0
        created_at        TEXT NOT NULL

    character_configs:
        character_name      TEXT PK
        display_name        TEXT DEFAULT ''
        avatar              TEXT DEFAULT ''
        signature           TEXT DEFAULT ''
        temperature         REAL DEFAULT 0.7
        reply_length        TEXT DEFAULT 'normal'
        tone                TEXT DEFAULT 'default'
        custom_instructions TEXT DEFAULT ''
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id                TEXT PRIMARY KEY,
                character         TEXT NOT NULL,
                type              TEXT DEFAULT 'single',
                title             TEXT DEFAULT '',
                scene_background  TEXT DEFAULT '',
                absent_characters TEXT DEFAULT '[]',
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL,
                message_count     INTEGER DEFAULT 0,
                preview           TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                is_bot          INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id);

            CREATE TABLE IF NOT EXISTS character_configs (
                character_name      TEXT PRIMARY KEY,
                display_name        TEXT DEFAULT '',
                avatar              TEXT DEFAULT '',
                signature           TEXT DEFAULT '',
                temperature         REAL DEFAULT 0.7,
                reply_length        TEXT DEFAULT 'normal',
                tone                TEXT DEFAULT 'default',
                custom_instructions TEXT DEFAULT ''
            );
        """)

        # ── 迁移：为 character_configs 增加新列（兼容已有数据库） ──
        _NEW_CONFIG_COLS = [
            "title TEXT DEFAULT ''",
            "description TEXT DEFAULT ''",
            "api_url TEXT DEFAULT ''",
            "model TEXT DEFAULT ''",
            "api_key TEXT DEFAULT ''",
        ]
        for col_def in _NEW_CONFIG_COLS:
            col_name = col_def.split()[0]
            try:
                conn.execute(f"ALTER TABLE character_configs ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # ── 迁移：conversations 增加 player_character 列 ──
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN player_character TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists


# ===================================================================
#  Conversation CRUD
# ===================================================================

def get_all_conversations() -> list[dict]:
    """获取所有对话，按 updated_at DESC 排序。

    Returns:
        对话 dict 列表，每个 dict 含所有列，其中 absent_characters 被解析为 list。
        无对话时返回空列表。
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_conversation(conv_id: str) -> Optional[dict]:
    """获取单个对话（不含消息），不存在返回 None。

    Returns:
        对话 dict（含所有列），或 None。
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def create_conversation(
    conv_id: str,
    character: str,
    type_: str = "single",
    title: str = "",
    scene_background: str = "",
    absent_characters: Any = "[]",
    player_character: str = "",
) -> dict:
    """创建新对话。

    如果 conv_id 已存在，会覆盖更新（upsert 语义），
    但不会重置 created_at / message_count / preview。

    Args:
        conv_id:             对话 ID（由调用方生成，如 "conv_xxxx"）
        character:           对话关联的主要角色名
        type_:               对话类型：'single' | 'group'
        title:               对话标题
        scene_background:    场景背景描述
        absent_characters:   缺席角色列表（str JSON 或 list）

    Returns:
        创建后的对话 dict。
    """
    now = _now()
    absent_str = _ensure_json_array(absent_characters)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations
                (id, character, type, title, scene_background,
                 absent_characters, created_at, updated_at, player_character)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                character         = excluded.character,
                type              = excluded.type,
                title             = excluded.title,
                scene_background  = excluded.scene_background,
                absent_characters = excluded.absent_characters,
                player_character  = excluded.player_character,
                updated_at        = excluded.updated_at
            """,
            (conv_id, character, type_, title,
             scene_background, absent_str, now, now, player_character),
        )
    return get_conversation(conv_id)


def delete_conversation(conv_id: str) -> bool:
    """删除对话及其所有消息（CASCADE 删除消息）。

    Args:
        conv_id: 对话 ID。

    Returns:
        True 如果找到了并删除了对话，否则 False。
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conv_id,)
        )
        return cursor.rowcount > 0


def update_conversation_scene(
    conv_id: str,
    scene_background: Optional[str] = None,
    absent_characters: Any = None,
) -> Optional[dict]:
    """更新对话的场景背景与缺席角色（支持部分更新）。

    Args:
        conv_id:           对话 ID。
        scene_background:  新的场景背景描述；None 表示不更新此字段。
        absent_characters: 新的缺席角色列表（str JSON 或 list）；None 表示不更新。

    Returns:
        更新后的对话 dict，不存在返回 None。
    """
    now = _now()
    sets: list[str] = ["updated_at = ?"]
    params: list[Any] = [now]
    if scene_background is not None:
        sets.append("scene_background = ?")
        params.append(scene_background)
    if absent_characters is not None:
        sets.append("absent_characters = ?")
        params.append(_ensure_json_array(absent_characters))
    params.append(conv_id)
    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE conversations SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        if cursor.rowcount == 0:
            return None
    return get_conversation(conv_id)


# ===================================================================
#  Message CRUD
# ===================================================================

def get_messages(conv_id: str) -> list[dict]:
    """获取对话的所有消息，按 id ASC 排序。

    Returns:
        消息 dict 列表。无消息时返回空列表。
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_message(
    conv_id: str,
    role: str,
    content: str,
    is_bot: int = 0,
) -> Optional[dict]:
    """添加消息，并自动更新对话的 message_count、preview、updated_at。

    如果 conv_id 不存在（无对应对话），消息不会被插入，函数返回 None。

    Args:
        conv_id: 对话 ID。
        role:    角色名或 'user'。
        content: 消息内容。
        is_bot:  是否为 bot 消息（1 / 0）。

    Returns:
        新消息的 dict（含自增 id），或 None（对话不存在时）。
    """
    now = _now()
    with get_connection() as conn:
        # 先检查对话是否存在
        exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        if not exists:
            return None

        cursor = conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, is_bot, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conv_id, role, content, int(is_bot), now),
        )
        msg_id = cursor.lastrowid

        # 更新对话统计
        preview = content[:_MAX_PREVIEW_LENGTH].replace("\n", " ")
        conn.execute(
            """
            UPDATE conversations
            SET message_count = message_count + 1,
                preview       = ?,
                updated_at    = ?
            WHERE id = ?
            """,
            (preview, now, conv_id),
        )

    return {
        "id": msg_id,
        "conversation_id": conv_id,
        "role": role,
        "content": content,
        "is_bot": int(is_bot),
        "created_at": now,
    }


# ===================================================================
#  批量导入（从 localStorage 迁移用）
# ===================================================================

def batch_import_conversations(
    convs: list[dict],
    messages_map: dict[str, list[dict]],
) -> int:
    """批量导入对话及消息，按 id 跳过已存在的。

    用于前端 localStorage 数据迁移。不会覆盖已有记录。

    Args:
        convs:         对话 dict 列表。每个 dict 应包含与 conversations 表列对应的键。
        messages_map:  映射 {conversation_id: [message_dict, ...]}。
                       每个 message dict 应包含 role / content / is_bot 等。
                       也兼容前端格式（character / text / isBot 键）。

    Returns:
        实际导入的对话数量。
    """
    now = _now()
    imported = 0

    with get_connection() as conn:
        # 获取已有 ID
        existing_ids: set[str] = {
            row["id"]
            for row in conn.execute("SELECT id FROM conversations").fetchall()
        }

        for conv in convs:
            conv_id = conv.get("id", "")
            if not conv_id or conv_id in existing_ids:
                continue

            # 插入对话
            conn.execute(
                """
                INSERT INTO conversations
                    (id, character, type, title, scene_background,
                     absent_characters, created_at, updated_at,
                     message_count, preview)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conv_id,
                    conv.get("character", conv.get("partner", "")),
                    conv.get("type", "single"),
                    conv.get("title", ""),
                    conv.get("scene_background", ""),
                    _ensure_json_array(
                        conv.get("absent_characters", conv.get("absentCharacters", []))
                    ),
                    conv.get("created_at", conv.get("createdAt", now)),
                    conv.get("updated_at", conv.get("updatedAt", now)),
                    conv.get("message_count", conv.get("messageCount", 0)),
                    conv.get("preview", ""),
                ),
            )

            # 插入消息（容忍前端与后端两种字段命名风格）
            for msg in messages_map.get(conv_id, []):
                row = _dict_to_message_row(msg)
                row["conversation_id"] = conv_id  # 覆盖为当前对话 ID
                conn.execute(
                    """
                    INSERT INTO messages
                        (conversation_id, role, content, is_bot, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (row["conversation_id"], row["role"],
                     row["content"], row["is_bot"], row["created_at"]),
                )

            imported += 1
            existing_ids.add(conv_id)

    return imported


# ===================================================================
#  Character Config CRUD
# ===================================================================

def get_all_character_configs() -> list[dict]:
    """获取所有角色配置。

    Returns:
        角色配置 dict 列表。无配置时返回空列表。
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM character_configs").fetchall()
        return [dict(r) for r in rows]


def get_character_config(name: str) -> Optional[dict]:
    """获取单个角色配置，不存在返回 None。

    Returns:
        角色配置 dict，或 None。
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM character_configs WHERE character_name = ?",
            (name,),
        ).fetchone()
        return dict(row) if row else None


def upsert_character_config(name: str, data: dict) -> dict:
    """插入或更新角色配置。

    只处理 data 中属于允许字段的键：
        display_name, avatar, signature, temperature,
        reply_length, tone, custom_instructions

    如果 data 没有这些字段且配置不存在，将用默认值创建一条记录。

    Args:
        name: 角色名（PK）。
        data: 包含要更新的字段的 dict。

    Returns:
        更新后的角色配置 dict。
    """
    filtered = {k: v for k, v in data.items() if k in _ALLOWED_CONFIG_FIELDS}

    with get_connection() as conn:
        if filtered:
            columns = list(filtered.keys())
            placeholders = ", ".join("?" for _ in columns)
            set_clause = ", ".join(f"{k} = excluded.{k}" for k in columns)
            all_columns = ", ".join(columns)

            conn.execute(
                f"""
                INSERT INTO character_configs (character_name, {all_columns})
                VALUES (?, {placeholders})
                ON CONFLICT(character_name) DO UPDATE SET
                    {set_clause}
                """,
                (name, *filtered.values()),
            )
        else:
            # 没有要设置的字段，确保行存在（用默认值）
            conn.execute(
                """
                INSERT INTO character_configs (character_name)
                VALUES (?)
                ON CONFLICT(character_name) DO NOTHING
                """,
                (name,),
            )

    return get_character_config(name)
