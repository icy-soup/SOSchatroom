# P1–P2: SQLite Persistence + Scene Settings + Character Edit Panel

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace client-side localStorage with SQLite backend persistence, add scene settings (background + absent characters), and add character edit panel (avatar/name/signature + behavior tuning).

**Architecture:** New `backend/database.py` module owns all SQLite operations. New REST endpoints in `main.py` expose CRUD. Frontend gets a new `api.ts` layer to call REST endpoints, replacing direct localStorage reads/writes. Scene settings injected into `build_system_prompt()`; absent characters filtered in `select_responders()`. Character config stored in new `character_configs` table, loaded in `App.tsx` and passed to components.

**Tech Stack:** Python `sqlite3` (stdlib), FastAPI routes, React fetch API, existing WebSocket flow unchanged.

---

### Task 1: Backend — database.py

**Files:**
- Create: `backend/database.py`

```python
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "chatroom.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            character TEXT NOT NULL,
            type TEXT DEFAULT 'single',
            title TEXT DEFAULT '',
            scene_background TEXT DEFAULT '',
            absent_characters TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            preview TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            is_bot INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE TABLE IF NOT EXISTS character_configs (
            character_name TEXT PRIMARY KEY,
            display_name TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            signature TEXT DEFAULT '',
            temperature REAL DEFAULT 0.7,
            reply_length TEXT DEFAULT 'normal',
            tone TEXT DEFAULT 'default',
            custom_instructions TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
    """)
    conn.commit()
    conn.close()

# === Conversation CRUD ===

def get_all_conversations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, character, type, title, scene_background, absent_characters, "
        "created_at, updated_at, message_count, preview "
        "FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(conv_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_conversation(conv_id: str, character: str, conv_type: str = "single",
                        title: str = "", scene_background: str = "", absent_characters: str = "[]"):
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (id, character, type, title, scene_background, absent_characters, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (conv_id, character, conv_type, title, scene_background, absent_characters, now, now)
    )
    conn.commit()
    conn.close()

def delete_conversation(conv_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
    conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
    conn.commit()
    conn.close()

def update_conversation_scene(conv_id: str, scene_background: str = None, absent_characters: str = None):
    now = datetime.now().isoformat()
    fields = ["updated_at=?"]
    params = [now]
    if scene_background is not None:
        fields.append("scene_background=?")
        params.append(scene_background)
    if absent_characters is not None:
        fields.append("absent_characters=?")
        params.append(absent_characters)
    params.append(conv_id)
    conn = get_connection()
    conn.execute(f"UPDATE conversations SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()

# === Message CRUD ===

def get_messages(conv_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, conversation_id, role, content, is_bot, created_at "
        "FROM messages WHERE conversation_id=? ORDER BY id ASC",
        (conv_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_message(conv_id: str, role: str, content: str, is_bot: int = 0):
    now = datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO messages (conversation_id, role, content, is_bot, created_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, role, content, is_bot, now)
    )
    # Update conversation stats
    preview = content[:50] if len(content) > 50 else content
    conn.execute(
        "UPDATE conversations SET message_count=message_count+1, preview=?, updated_at=? WHERE id=?",
        (preview, now, conv_id)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def batch_import_conversations(convs: list, messages_map: dict):
    """Import conversations and their messages. Skip existing by id."""
    conn = get_connection()
    existing_ids = set(
        row[0] for row in conn.execute("SELECT id FROM conversations").fetchall()
    )
    for conv in convs:
        if conv["id"] in existing_ids:
            continue
        conn.execute(
            "INSERT INTO conversations (id, character, type, title, scene_background, absent_characters, created_at, updated_at, message_count, preview) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (conv["id"], conv.get("character", ""), conv.get("type", "single"),
             conv.get("title", ""), conv.get("scene_background", ""), conv.get("absent_characters", "[]"),
             conv.get("created_at", now), conv.get("updated_at", now),
             conv.get("message_count", 0), conv.get("preview", ""))
        )
        msgs = messages_map.get(conv["id"], [])
        for msg in msgs:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, is_bot, created_at) VALUES (?, ?, ?, ?, ?)",
                (conv["id"], msg.get("role", ""), msg.get("content", ""),
                 msg.get("is_bot", 0), msg.get("created_at", now))
            )
    conn.commit()
    conn.close()

# === Character Config CRUD ===

def get_all_character_configs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM character_configs").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_character_config(name: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM character_configs WHERE character_name=?", (name,)).fetchall()
    conn.close()
    return dict(row[0]) if row else None

def upsert_character_config(name: str, data: dict):
    allowed = ["display_name", "avatar", "signature", "temperature", "reply_length", "tone", "custom_instructions"]
    fields = []
    values = []
    for key in allowed:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    if not fields:
        return
    values.append(name)
    conn = get_connection()
    conn.execute(
        f"INSERT INTO character_configs (character_name, {', '.join(allowed)}) "
        f"VALUES (?, {', '.join('?' for _ in allowed)}) "
        f"ON CONFLICT(character_name) DO UPDATE SET {', '.join(fields)}",
        [name] + [data.get(k, "") for k in allowed] + values
    )
    conn.commit()
    conn.close()
```

---

### Task 2: Backend — REST API endpoints for conversations

**Files:**
- Modify: `backend/main.py`

Add these imports at top:
```python
from database import (
    init_db, get_all_conversations, get_conversation, create_conversation,
    delete_conversation, update_conversation_scene,
    get_messages, add_message, batch_import_conversations
)
```

Add after existing endpoints (after line 380 or so, before the WS endpoint):

```python
@app.on_event("startup")
def startup():
    init_db()

# === Conversation API ===

@app.get("/api/conversations")
async def list_conversations():
    convs = get_all_conversations()
    return {"conversations": convs}

@app.post("/api/conversations")
async def new_conversation(data: dict):
    import uuid
    conv_id = str(uuid.uuid4())
    character = data.get("character", "")
    conv_type = data.get("type", "single")
    title = data.get("title", "")
    scene_background = data.get("scene_background", "")
    absent_characters = json.dumps(data.get("absent_characters", []))
    create_conversation(conv_id, character, conv_type, title, scene_background, absent_characters)
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

@app.post("/api/conversations/batch-import")
async def batch_import(data: dict):
    convs = data.get("conversations", [])
    messages_map = data.get("messages", {})
    batch_import_conversations(convs, messages_map)
    return {"ok": True, "count": len(convs)}
```

Add `import json` at top of file.

---

### Task 3: Backend — REST API for character configs

**Files:**
- Modify: `backend/main.py`

Add after conversation API endpoints:

```python
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
```

---

### Task 4: Backend — WebSocket auto-persistence + scene integration

**Files:**
- Modify: `backend/main.py` — save messages to SQLite
- Modify: `backend/engine/character.py` — inject scene background
- Modify: `backend/engine/trigger.py` — filter absent characters

**4a: Auto-persist messages in WebSocket handler**
In `main.py`, inside the `if data["type"] == "message":` block:
- After appending user message to `session["history"]`, call `add_message(conv_id, role, content, is_bot=0)`
- After appending each bot response to `session["history"]`, call `add_message(conv_id, role, content, is_bot=1)`

Where does conv_id come from? Add it to the `join` message and store in session.
In `if data["type"] == "join":`, after setting session character:
```python
session["conversation_id"] = data.get("conversation_id", "")
```

Then in the `message` handler, after user msg:
```python
if session.get("conversation_id"):
    add_message(session["conversation_id"], session.get("player_character", "你"), text, is_bot=0)
```

After each bot response:
```python
if session.get("conversation_id"):
    add_message(session["conversation_id"], responder, sanitized, is_bot=1)
```

**4b: Inject scene background into system prompt**
Modify `build_system_prompt()` in `engine/character.py`:
```python
def build_system_prompt(name, scene_background="", custom_instructions=""):
    skill_text = load_skill(name)
    prompt = f"你是{name}。\n\n{skill_text}\n\n回复规则：..."
    if scene_background:
        prompt += f"\n\n[当前场景]\n{scene_background}"
    if custom_instructions:
        prompt += f"\n\n[额外指令]\n{custom_instructions}"
    return prompt
```

Update the call site in `main.py` WS message handler:
```python
system_prompt = build_system_prompt(
    responder,
    scene_background=session.get("scene_background", ""),
    custom_instructions=session.get("custom_instructions", "")
)
```

Scene background needs to be loaded from SQLite on `join`. After `join`, if `conversation_id` is set:
```python
conv = get_conversation(session["conversation_id"])
if conv:
    session["scene_background"] = conv.get("scene_background", "")
    session["absent_characters"] = json.loads(conv.get("absent_characters", "[]"))
```

Also handle `update_scene` WS message:
```python
if data["type"] == "update_scene":
    session["scene_background"] = data.get("scene_background", "")
    session["absent_characters"] = data.get("absent_characters", [])
    if session.get("conversation_id"):
        update_conversation_scene(
            session["conversation_id"],
            scene_background=data.get("scene_background"),
            absent_characters=json.dumps(data.get("absent_characters", []))
        )
    await ws.send_json({"type": "scene_updated", "ok": True})
```

**4c: Filter absent characters in select_responders**
Modify `select_responders()` in `engine/trigger.py` to accept an `absent: list[str] = None` parameter:
```python
def select_responders(last_speaker, message_text, user_character, existing_responders,
                      conversation_history, absent=None):
    # ... existing logic ...
    candidates = [...]  # from existing logic
    if absent:
        candidates = [c for c in candidates if c not in absent]
    return candidates
```

Update call site in `main.py`:
```python
responders = select_responders(
    last_speaker, text, player_character,
    existing_responders, session["history"],
    absent=session.get("absent_characters", [])
)
```

---

### Task 5: Frontend — API client + type updates

**Files:**
- Create: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`

**5a: Create `frontend/src/api.ts`**
```typescript
const BASE = "/api";

async function fetchJSON(url: string, options?: RequestInit) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
}

export interface ConversationDTO {
  id: string;
  character: string;
  type: "single" | "group";
  title: string;
  scene_background: string;
  absent_characters: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  preview: string;
}

export interface MessageDTO {
  id: number;
  conversation_id: string;
  role: string;
  content: string;
  is_bot: number;
  created_at: string;
}

export interface CharacterConfigDTO {
  character_name: string;
  display_name: string;
  avatar: string;
  signature: string;
  temperature: number;
  reply_length: string;
  tone: string;
  custom_instructions: string;
}

export async function fetchConversations(): Promise<{ conversations: ConversationDTO[] }> {
  return fetchJSON(`${BASE}/conversations`);
}

export async function createConversation(data: {
  character: string;
  type: string;
  title?: string;
  scene_background?: string;
  absent_characters?: string[];
}): Promise<{ id: string }> {
  return fetchJSON(`${BASE}/conversations`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchConversationDetail(id: string): Promise<{
  conversation: ConversationDTO;
  messages: MessageDTO[];
}> {
  return fetchJSON(`${BASE}/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await fetchJSON(`${BASE}/conversations/${id}`, { method: "DELETE" });
}

export async function updateScene(
  id: string,
  data: { scene_background?: string; absent_characters?: string[] }
): Promise<void> {
  await fetchJSON(`${BASE}/conversations/${id}/scene`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function batchImportConversations(data: {
  conversations: any[];
  messages: Record<string, any[]>;
}): Promise<void> {
  await fetchJSON(`${BASE}/conversations/batch-import`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchCharacterConfigs(): Promise<{ configs: CharacterConfigDTO[] }> {
  return fetchJSON(`${BASE}/character-configs`);
}

export async function fetchCharacterConfig(name: string): Promise<{ config: CharacterConfigDTO | null }> {
  return fetchJSON(`${BASE}/character-configs/${name}`);
}

export async function updateCharacterConfig(name: string, data: Partial<CharacterConfigDTO>): Promise<void> {
  await fetchJSON(`${BASE}/character-configs/${name}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
```

**5b: Update `frontend/src/types.ts`** — add scene fields to Conversation:
```typescript
interface Conversation {
  id: string;
  partner: string;
  playerCharacter: string;
  title: string;
  messages: Message[];
  createdAt: number;
  sceneBackground?: string;      // P1.5
  absentCharacters?: string[];   // P1.5
}
```

Also add `scene_updated` to WsMessage type:
```typescript
| { type: "scene_updated"; ok: boolean }
```

---

### Task 6: Frontend — Scene settings UI

**Files:**
- Create: `frontend/src/components/SceneSettingsPanel.tsx`
- Modify: `frontend/src/components/NewConversationView.tsx`
- Modify: `frontend/src/components/ChatHeader.tsx`

**6a: Create `SceneSettingsPanel.tsx`** — reusable collapsible panel:
```tsx
interface SceneSettingsPanelProps {
  background: string;
  absent: string[];
  allCharacters: string[];
  onBackgroundChange: (v: string) => void;
  onAbsentChange: (v: string[]) => void;
}

function SceneSettingsPanel({ background, absent, allCharacters, onBackgroundChange, onAbsentChange }: SceneSettingsPanelProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-gray-700 mt-3 pt-3">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-sm text-gray-400 hover:text-white">
        {open ? "▲" : "▼"} 场景设置 {!open && (background || absent.length > 0) && <span className="text-cyan-400">(已设置)</span>}
      </button>
      {open && (
        <div className="mt-2 space-y-3">
          <div>
            <label className="text-xs text-gray-400">场景背景词</label>
            <textarea className="w-full bg-gray-800 text-sm rounded p-2 mt-1 border border-gray-600"
              rows={3} placeholder="今天放学后春日说想去山上抓外星人……" value={background}
              onChange={e => onBackgroundChange(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-400">缺席角色</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {allCharacters.map(name => (
                <button key={name} onClick={() => {
                  onAbsentChange(absent.includes(name) ? absent.filter(a => a !== name) : [...absent, name]);
                }} className={`px-2 py-1 text-xs rounded border ${absent.includes(name) ? 'border-red-500 text-red-400 bg-red-900/20' : 'border-gray-600 text-gray-300'}`}>
                  {absent.includes(name) ? `✕ ${name}` : name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

**6b: Modify `NewConversationView.tsx`** — add SceneSettingsPanel at bottom of step 2, pass values to createConversation call.

Add imports and state:
```typescript
import SceneSettingsPanel from './SceneSettingsPanel';
const [sceneBackground, setSceneBackground] = useState('');
const [absentCharacters, setAbsentCharacters] = useState<string[]>([]);
```

Render before the create button:
```tsx
<SceneSettingsPanel
  background={sceneBackground}
  absent={absentCharacters}
  allCharacters={CHARACTERS.map(c => c.name)}
  onBackgroundChange={setSceneBackground}
  onAbsentChange={setAbsentCharacters}
/>
```

In create handler, pass scene data:
```typescript
const convId = await createConversation({
  character: partner,
  type: partner === "group" ? "group" : "single",
  scene_background: sceneBackground,
  absent_characters: absentCharacters,
});
```

**6c: Modify `ChatHeader.tsx`** — add 🎬 button + scene modal.

- Add state for `showSceneModal: boolean`
- Add 🎬 button next to existing buttons (or instead of "清除")
- Modal shows SceneSettingsPanel + save button
- Save calls `send({type: "update_scene", scene_background, absent_characters})`

---

### Task 7: Frontend — Smooth migration + replace localStorage

**Files:**
- Modify: `frontend/src/App.tsx`

**Migration logic** (add after initial state setup, in useEffect on mount):
```typescript
// On mount, check localStorage for data to migrate
useEffect(() => {
  const existing = localStorage.getItem('sos_conversations');
  if (existing) {
    try {
      const data = JSON.parse(existing);
      if (Array.isArray(data) && data.length > 0) {
        // Convert to API format
        const conversations = data.map(c => ({
          id: c.id,
          character: c.partner,
          type: c.partner === 'SOS团聊天室' ? 'group' : 'single',
          title: c.title || `${c.partner} · 扮演${c.playerCharacter}`,
          scene_background: c.sceneBackground || '',
          absent_characters: JSON.stringify(c.absentCharacters || []),
          created_at: new Date(c.createdAt).toISOString(),
          updated_at: new Date(c.createdAt).toISOString(),
          message_count: c.messages?.length || 0,
          preview: c.messages?.[c.messages.length - 1]?.text?.slice(0, 50) || '',
        }));
        const messagesMap: Record<string, any[]> = {};
        data.forEach(c => {
          messagesMap[c.id] = (c.messages || []).map((m: any) => ({
            conversation_id: c.id,
            role: m.character || '你',
            content: m.text,
            is_bot: m.isBot ? 1 : 0,
            created_at: new Date().toISOString(),
          }));
        });
        batchImportConversations({ conversations, messages: messagesMap }).then(() => {
          localStorage.removeItem('sos_conversations');
          loadConversations(); // reload from API
        });
      }
    } catch (e) {
      console.error('Migration failed', e);
    }
  }
}, []);
```

**Replace localStorage with API calls:**
- `loadConversations()`: call `fetchConversations()` instead of `localStorage.getItem`
- `createConversation`: call `createConversation()` API instead of pushing to local state
- `deleteConversation`: call `deleteConversation()` API
- Remove the `useEffect` that syncs conversations to localStorage
- When loading messages for a conversation: use `fetchConversationDetail(id)` and map `MessageDTO` to `Message` type

Message mapping:
```typescript
function mapMessageDTO(msg: MessageDTO): Message {
  return {
    character: msg.role,
    text: msg.content,
    isBot: msg.is_bot === 1,
    id: `msg-${msg.id}`,
  };
}
```

For the active conversation's messages, load from API when switching:
```typescript
async function loadMessages(convId: string) {
  const data = await fetchConversationDetail(convId);
  const msgs = data.messages.map(mapMessageDTO);
  setConversations(prev => prev.map(c =>
    c.id === convId ? { ...c, messages: msgs } : c
  ));
}
```

---

### Task 8: Frontend — Character edit panel

**Files:**
- Create: `frontend/src/components/CharacterEditModal.tsx`
- Modify: `frontend/src/components/ContactDetail.tsx`
- Modify: `frontend/src/types.ts` — add CharacterConfig type (or use from api.ts if already imported)

**8a: Create `CharacterEditModal.tsx`**:
```tsx
import { useState, useEffect } from 'react';
import { CHARACTERS } from '../characters';
import { fetchCharacterConfig, updateCharacterConfig, CharacterConfigDTO } from '../api';

interface Props {
  characterName: string;
  onClose: () => void;
  onSaved: () => void;
}

const AVATAR_OPTIONS = ['🎭', '👤', '🌟', '🎪', '🎯', '💫', '✨', '🔥', '🌙', '⭐'];

export default function CharacterEditModal({ characterName, onClose, onSaved }: Props) {
  const [config, setConfig] = useState<CharacterConfigDTO>({
    character_name: characterName, display_name: '', avatar: '',
    signature: '', temperature: 0.7, reply_length: 'normal', tone: 'default', custom_instructions: ''
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCharacterConfig(characterName).then(data => {
      if (data.config) setConfig(data.config);
      setLoading(false);
    });
  }, [characterName]);

  const save = async () => {
    await updateCharacterConfig(characterName, config);
    onSaved();
    onClose();
  };

  if (loading) return <div className="p-4 text-gray-400">加载中...</div>;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 rounded-lg w-[480px] max-h-[80vh] overflow-y-auto p-6 border border-gray-700" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">编辑角色 · {characterName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">✕</button>
        </div>

        {/* Avatar */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">头像</label>
          <div className="flex gap-2 flex-wrap">
            {AVATAR_OPTIONS.map(emoji => (
              <button key={emoji} onClick={() => setConfig({...config, avatar: emoji})}
                className={`w-10 h-10 text-xl flex items-center justify-center rounded ${config.avatar === emoji ? 'ring-2 ring-cyan-400 bg-cyan-900/30' : 'bg-gray-800 hover:bg-gray-700'}`}>
                {emoji}
              </button>
            ))}
          </div>
        </div>

        {/* Display Name */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">显示名称</label>
          <input className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm"
            value={config.display_name} onChange={e => setConfig({...config, display_name: e.target.value})} />
        </div>

        {/* Signature */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">签名</label>
          <input className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm"
            value={config.signature} onChange={e => setConfig({...config, signature: e.target.value})} />
        </div>

        <hr className="border-gray-700 mb-4" />

        {/* Temperature */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">温度: {config.temperature.toFixed(1)}</label>
          <input type="range" min="0" max="2" step="0.1" value={config.temperature}
            onChange={e => setConfig({...config, temperature: parseFloat(e.target.value)})}
            className="w-full accent-cyan-500" />
        </div>

        {/* Reply Length */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">回复长度</label>
          <div className="flex gap-2">
            {['short', 'normal', 'long'].map(v => (
              <button key={v} onClick={() => setConfig({...config, reply_length: v})}
                className={`px-3 py-1 text-xs rounded ${config.reply_length === v ? 'bg-cyan-600 text-white' : 'bg-gray-800 text-gray-300'}`}>
                {v === 'short' ? '简短' : v === 'normal' ? '适中' : '详细'}
              </button>
            ))}
          </div>
        </div>

        {/* Tone */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">语气</label>
          <div className="flex gap-2">
            {['default', 'lively', 'calm'].map(v => (
              <button key={v} onClick={() => setConfig({...config, tone: v})}
                className={`px-3 py-1 text-xs rounded ${config.tone === v ? 'bg-cyan-600 text-white' : 'bg-gray-800 text-gray-300'}`}>
                {v === 'default' ? '保持默认' : v === 'lively' ? '更活泼' : '更冷静'}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Instructions */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">自定义指令</label>
          <textarea className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" rows={3}
            placeholder="追加到角色 prompt 末尾的额外指令……"
            value={config.custom_instructions}
            onChange={e => setConfig({...config, custom_instructions: e.target.value})} />
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">取消</button>
          <button onClick={save} className="px-4 py-2 text-sm bg-cyan-600 rounded hover:bg-cyan-500">保存</button>
        </div>
      </div>
    </div>
  );
}
```

**8b: Modify `ContactDetail.tsx`** — add ✏️ edit button next to avatar:
```tsx
import CharacterEditModal from './CharacterEditModal';

// In the component:
const [showEdit, setShowEdit] = useState(false);

// Next to avatar:
<div className="relative">
  <div className="w-24 h-24 rounded-full bg-gray-700 flex items-center justify-center text-4xl">
    {charConfig?.avatar || char.emoji}
  </div>
  <button onClick={() => setShowEdit(true)}
    className="absolute -top-1 -right-1 w-8 h-8 bg-gray-800 rounded-full border border-gray-600 flex items-center justify-center hover:bg-gray-700">
    ✏️
  </button>
</div>

{/* Show display_name if set */}
{charConfig?.display_name && (
  <div className="text-lg text-gray-300">{charConfig.display_name}</div>
)}

{/* Show signature if set */}
{charConfig?.signature && (
  <div className="text-sm text-gray-500 italic">{charConfig.signature}</div>
)}

{showEdit && (
  <CharacterEditModal characterName={character.name} onClose={() => setShowEdit(false)} onSaved={onConfigSaved} />
)}
```

Also need to load character configs in `ContactDetail`:
```typescript
const [charConfig, setCharConfig] = useState<CharacterConfigDTO | null>(null);

useEffect(() => {
  fetchCharacterConfig(character.name).then(data => setCharConfig(data.config || null));
}, [character.name]);
```

---

### Task 9: Update project memory — add desktop packaging back to roadmap

**Files:**
- Modify: `C:\Users\Karen Lee\.claude\projects\F--Extra-Learning-github-haruhi-skill\memory\project-haruhi-skill.md`

Insert a new P5 (desktop packaging) after P4 in the 待实现功能 section (around line 68):

```
### P5: 桌面打包（远期规划）
- Electron → Tauri 迁移
- 打包为独立桌面应用
- 内置 SQLite 数据库 + 本地 LLM 或 API Key 配置
```

Also update the docs/chatroom-design.md to include P5.
