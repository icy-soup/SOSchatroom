# P1–P2: SQLite 持久化 + 场景设置 + 角色编辑面板

> 2026-05-27 | 对应项目记忆 P1/P1.5/P2

## 数据库 Schema

```sql
-- conversations: 对话会话（P1 + P1.5）
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    character TEXT NOT NULL,           -- 角色名 或 "group"
    type TEXT DEFAULT 'single',        -- 'single' | 'group'
    title TEXT DEFAULT '',
    scene_background TEXT DEFAULT '',   -- P1.5: 场景背景词
    absent_characters TEXT DEFAULT '[]',-- P1.5: 缺席角色 JSON 数组
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    preview TEXT DEFAULT ''
);

-- messages: 消息（P1）
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    is_bot INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- character_configs: 角色配置（P2）
CREATE TABLE character_configs (
    character_name TEXT PRIMARY KEY,
    display_name TEXT DEFAULT '',
    avatar TEXT DEFAULT '',
    signature TEXT DEFAULT '',
    temperature REAL DEFAULT 0.7,
    reply_length TEXT DEFAULT 'normal',  -- 'short' | 'normal' | 'long'
    tone TEXT DEFAULT 'default',         -- 'default' | 'lively' | 'calm'
    custom_instructions TEXT DEFAULT ''
);
```

## REST API

```
### P1 对话 CRUD
GET    /api/conversations              → 对话列表
POST   /api/conversations              → 新建 {character, type, scene_background?, absent_characters?}
GET    /api/conversations/{id}         → 对话完整消息
DELETE /api/conversations/{id}         → 删除对话
POST   /api/conversations/{id}/messages  → 手动添加消息（导入用）
POST   /api/conversations/batch-import   → 平滑迁移（批量导入全部）

### P1.5 场景设置
PATCH  /api/conversations/{id}/scene     → {scene_background, absent_characters}

### P2 角色配置
GET    /api/character-configs            → 所有角色配置
GET    /api/character-configs/{name}     → 单个角色配置
PUT    /api/character-configs/{name}     → 更新（完整覆盖）
```

## WebSocket 集成

- 发送消息时后端自动落盘：写 messages 表 + 更新 conversations 统计
- 修改场景：前端发 `type: "update_scene"` → 后端更新 conversations 表
- 场景词追加到 `build_system_prompt()` 末尾
- 缺席角色在 `select_responders()` 中过滤排除

## UI 组件变更

### NewConversationView
- 选角页底部加可折叠「场景设置」面板
- 含场景背景词 textarea + 缺席角色多选 toggle

### ChatHeader
- 右上角加 🎬 图标按钮，点击弹出场景修改面板
- 修改后从下一句生效

### ContactDetail
- 头像旁加 ✏️ 编辑按钮，点击弹出角色编辑 Modal

### CharacterEditModal（P2 新增组件）
- 基础资料：头像切换、显示名称、签名
- 行为微调：温度 slider、回复长度、语气
- 自定义指令 textarea
- 保存到 character_configs 表，不修改 SKILL.md

## 平滑迁移

1. 首次加载检测 localStorage 有 `sos_conversations`？
2. POST `/api/conversations/batch-import` 批量迁移
3. 去重策略：按 conversation id 比对，已存在则跳过
4. 成功后清空 localStorage

## 优先级

自定义指令 > 语气微调 > 温度 > SKILL 默认

## 后续计划

### P5: 桌面打包（远期规划）
- Electron → Tauri 迁移
- 打包为独立桌面应用
- 内置 SQLite 数据库 + 本地 LLM 或 API Key 配置
