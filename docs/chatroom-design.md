# SOS团聊天室 — 设计文档

> 更新：2026-05-27 | v3+ 角色编辑增强(可编辑头衔/介绍/独立API/模型) + 工具点子

## 项目结构

```
haruhi-skill/
├── backend/                     # FastAPI + WebSocket
│   ├── main.py                  # 入口、LLM、WebSocket
│   ├── config.py                # 角色映射、SKILL加载
│   ├── engine/
│   │   ├── trigger.py           # 触发层（谁回复）
│   │   ├── character.py         # 角色层（prompt构建）
│   │   └── style.py             # 风格层（对象别语气）
│   └── uploads/                 # 背景图片
├── frontend/                    # React + Vite + Tailwind
│   └── src/
│       ├── components/          # UI 组件
│       ├── hooks/               # useWebSocket
│       └── types.ts             # 类型定义
├── skills/characters/           # 5 角色 SKILL.md
│   ├── haruhi/SKILL.md
│   ├── kyon/SKILL.md
│   ├── nagato/SKILL.md
│   ├── asahina/SKILL.md
│   └── koizumi/SKILL.md
├── data/
│   ├── novels/                  # 小说原文（全13卷）
│   ├── dialogues/               # 标注对话（791条）
│   ├── analysis/                # 统计分析
│   └── scripts/                 # 挖掘分析脚本
├── docs/
│   ├── README.md                # 文档索引
│   └── chatroom-design.md       # 本文件
├── .env                         # API Key
└── chatroom.bat                 # 一键启动
```

## 架构

```
前端 (React) ← WebSocket → 后端 (FastAPI)
  └─ ws://localhost:8000/ws       └─ 会话管理
  └─ http://localhost:8000/api    └─ LLM 调用（Anthropic / OpenAI）
                                   └─ 三层响应引擎
```

## 三层响应引擎

```
触发层 (trigger.py)
  └─ @提及 → 强制回复
  └─ 直接提问 → 被问者回复
  └─ 独立概率 roll（基于小说条件概率矩阵）
  └─ 话题匹配补正 + 语境连贯补正
       ↓
角色层 (character.py)
  └─ 加载 SKILL.md → 构建 system prompt
  └─ 嵌入对话历史 → 提供上下文
       ↓
风格层 (style.py)
  └─ 根据说话对象调整语气（addressee关系矩阵）
       ↓
LLM 调用 (main.py)
  └─ Anthropic SDK / OpenAI SDK 双协议
  └─ 失败 → 演示模式兜底
```

## 风格化交互设计（2026-05-27 改造）

### 新设计（当前状态 2026-05-27 v2）

#### 整体流程图

```
                    ┌──────────────────────────────┐
                    │         idle (待输入)         │
                    │  Enter → 触发风格化           │
                    └──────────┬───────────────────┘
                               │ Enter
                               ▼
                    ┌──────────────────────────────┐
                    │       stylizing (风格化中)    │
                    │  按钮禁止点击，等待后端返回    │
                    └──────────┬───────────────────┘
                               │ 后端返回 stylized 结果
                               ▼
               ┌───────────────────┬───────────────────┐
               │                   │                   │
               ▼                   ▼                   ▼
    ┌────────────────────┐ ┌────────────────────┐
    │  already_character  │ │     stylized        │
    │ 原文已符合角色特征   │ │ 输入框替换为风格化版本 │
    │ 显示匹配度分数+鼓励  │ │ 显示"✨已风格化"+分数  │
    │ Enter=直接发送      │ │ Enter=发送风格化版本   │
    └────────┬───────────┘ │ Esc=还原原文           │
             │             │ 编辑=重置→idle(可重风格化)
             │             └────────┬──────────────┘
             │                      │
             │  还原后              │ Esc 还原后
             ▼                      ▼
    ┌────────────────────┐
    │  restored(已还原)   │
    │ Esc→显示"已还原原文"│
    │ Enter=直接发送原文  │
    │ 编辑=重置→idle      │
    └────────┬───────────┘
             │
             │ 编辑文字
             ▼
    ┌────────────────────┐
    │      idle          │ ← 回到起点，可重新风格化
    │  Enter=重新风格化   │
    └────────────────────┘
```

#### 状态机

```
idle ──Enter──→ stylizing ──后端返回──→ stylized
                                         │  ├──Enter──→ 发送(发送后回到idle)
                                         │  ├──Esc──→ idle(还原原文,但带"已还原"标记)
                                         │  └──编辑──→ idle(可重风格化)
                                         │
                    already_character ────┤
                      ├──Enter──→ 发送(直接发原文)
                      ├──编辑──→ idle(可重风格化)
                      └──(来自后端判断原文已符合角色)
```

#### 核心规则

- 第一次 Enter 触发风格化（非发送）
- 风格化后输入框内容被替换为角色语气版本
- 再次 Enter → 发送当前文本（风格化版本或已还原的原文）
- Esc → 还原为原始文本，显示「已还原原文，Enter 直接发送」
- 编辑后状态重置为 idle，可再次 Enter 风格化
- 如果文本已符合角色特征（启发式检测），跳过风格化，显示匹配度分数

#### 匹配度评分

- 后端 `check_character_match()` 启发式检测（关键词匹配）
- 返回 `score: 0-1`，前端显示「原角色匹配度: XX%」
- 分数>0.25 判定为已符合角色特征，走 `already_character` 分支

#### 后端 API

- WebSocket 消息 `type: "stylize"` → 返回 `type: "stylized"`
- `check_character_match()` 启发式检测（关键词 + 句式匹配）
- 风格化调用复用现有 LLM pipeline（prompt 强调改写而非回复）
- 返回字段：`{ original, transformed, already_in_character, message, score }`

#### 已知问题

- 匹配度评分是启发式的（关键词匹配），精度有限
- LLM 有时仍会把风格化理解为「以角色身份回复」而非「改写原句」
- 风格化/发送的键盘流与鼠标点击流逻辑需保持一致（两套入口）

## 待实现功能

### P0: 三栏微信布局（已实现 · 2026-05-27 v2）

#### 组件树

```
App
├── IconBar (54px)            ← 深色图标栏，始终显示
│   ├── 💬 聊天              ← 默认激活
│   ├── 👥 联系人
│   ├── 🛠 工具
│   └── ⚙ 设置              ← SettingsModal
│
├── MiddlePanel (280px)       ← 中间栏，始终显示
│   ├── ChatList              ← 💬 激活时
│   │   ├── 每条: 头像+默认名+编辑按钮+时间
│   │   ├── 默认名格式: "{角色} · 扮演{我}"
│   │   ├── 点击编辑按钮→内联重命名（类似DeepSeek网页版）
│   │   ├── 点击加载对话
│   │   └── "新建对话" 按钮
│   ├── ContactList           ← 👥 激活时
│   │   ├── 个人类别: 5角色
│   │   └── 群聊类别: SOS团聊天室
│   ├── ToolList              ← 🛠 激活时
│   │   └── 3个SOS工具
│   └── HistoryList           ← 📁 激活时
│       └── (SQLite P2)
│
├── RightPanel (flex-1)       ← 右侧主面板，根据上下文变化
│   ├── ChatView              ← 💬 + 选中对话
│   │   ├── ChatHeader (角色名+操作)
│   │   ├── MessageFlow
│   │   └── InputArea / CharacterSelectorBar
│   ├── ContactDetailView     ← 👥 + 点联系人
│   │   ├── 角色头像(大)
│   │   ├── 角色名称+头衔
│   │   ├── 签名/自我介绍
│   │   └── 「发起新对话」按钮
│   ├── NewChatView           ← 👥 + 发起新对话
│   │   ├── 选择扮演角色
│   │   └── 确认后切换到聊天
│   ├── ToolDetailView        ← 🛠 + 选中工具
│   │   ├── 工具标题+描述
│   │   ├── Textarea输入
│   │   └── 结果展示
│   └── WelcomeView           ← 默认/未选中
│       └── 背景+提示文字
│
└── SettingsModal             ← 设置（API Key等）
```

#### 交互规则

- 三栏永远显示，IconBar 切换中间栏和右侧的内容
- 切换图标时，右侧面板跟着变化（聊天→联系人→工具→历史）
- 聊天列表默认名: "{聊天对象} · 扮演{我}"，点击编辑按钮内联重命名
- 联系人: 点击→右侧显示人物介绍页；「发起新对话」→选择扮演角色→切换到聊天
- 工具: 点击→中间栏显示工具列表，右侧显示工具操作界面（不保留聊天）
- 角色未选择时显示 CharacterSelectorBar

### P1: SQLite 对话持久化（已实现 · 2026-05-27 v3）

#### 现状

- 已用 `backend/database.py` SQLite 替换 localStorage
- 所有对话和消息持久化到 `backend/chatroom.db`
- 平滑迁移：首次加载自动从 localStorage 导入

#### 数据库结构（已实现）

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    character TEXT NOT NULL,      -- 角色名 或 "group"
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
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
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
```

#### API（已实现）

```
GET    /api/conversations              → 对话列表
POST   /api/conversations              → 新建
GET    /api/conversations/{id}         → 对话+消息
DELETE /api/conversations/{id}         → 删除
PATCH  /api/conversations/{id}/scene   → 更新场景
POST   /api/conversations/batch-import → 批量导入
GET    /api/character-configs          → 所有角色配置
GET    /api/character-configs/{name}   → 单个角色配置
PUT    /api/character-configs/{name}   → 更新角色配置
POST   /api/upload-avatar/{name}       → 上传角色头像
```

WebSocket 消息自动落盘（`add_message()`）。

### P1.5: 对话场景设置（已实现 · 2026-05-27 v3）

每条对话可设置场景基调 + 角色出勤，适用于单人对话和群聊，保存在 conversations 表：

```
对话设置面板（在 ChatHeader 或聊天列表右键菜单进入）
├── 场景背景词 (textarea)
│   └── "今天放学后春日说想去山上抓外星人……"
│   └── 作为 system prompt 追加到该对话的 LLM 调用中
│   └── 可在对话中途修改（角色会感知变化：聊着聊着春日又开心了）
├── 缺席角色 (多选 toggle)
│   └── 勾选的角色不会在对话中出现
│   └── 后端过滤 responders 时排除
│   └── 默认全员出席
└── 未设置时使用默认行为
```

**实现方式**:

- 场景词: 追加到 `build_system_prompt()` 末尾，每条消息调用时传入
- 缺席角色: 后端 `select_responders` 后在 partner 过滤之前排除
- 对话中途修改：前端发 WebSocket 消息更新 session 中的场景/缺席列表

### P2: 角色编辑面板（已实现 · 2026-05-27 v3）

允许用户在界面上编辑角色资料和微调行为，从联系人详情页进入：

```
角色编辑面板（ContactDetail ✏️ 按钮进入）
├── 基础资料
│   ├── 头像切换（预制 emoji 12个 + 用户上传图片）
│   ├── 显示名称（不修改SKILL，仅UI显示用）
│   └── 签名/介绍（UI显示用，默认显示角色原文台词）
├── 行为微调
│   ├── System Prompt 温度 (slider 0-2)
│   ├── 回复长度偏好 (简短/适中/详细)
│   ├── 语气微调 (更活泼/更冷静/保持默认)
│   └── 自定义指令 (textarea, 追加到system prompt末尾)
└── 每个角色独立配置
```

**存储方式**: `character_configs` 表（SQLite）
**优先级**: 自定义指令 > 语气微调 > 温度 > SKILL默认
**头像上传**: `POST /api/upload-avatar/{name}` → 保存到 `uploads/avatars/` → 更新 avatar 字段
**注意**: 所有编辑是前端UI覆盖层，不影响 SKILL.md 原始数据

#### P2.5: 角色编辑面板增强（待实现）

- 头像上传支持裁切/缩放
- **自定义表情包管理**：每个角色绑定一组表情，在对应场景/情绪下自动发送（见 P6）
- 编辑面板 UI 重新设计（当前为简单 modal，后续可能改为独立页面或分 tab）

### P6: 角色表情包系统（待实现）

角色在聊天中发送表情/贴图，增强表现力：

```
表情包系统
├── 默认表情包
│   ├── 每个角色预置 8-12 个表情（聊天中自动匹配场景发送）
│   ├── 触发条件：关键词匹配、对话氛围、情绪状态
│   ├── 发送方式：纯表情 / 文字+表情
│   └── 频率控制：每条对话最多 1 个表情，不刷屏
├── 用户自定义
│   ├── 角色编辑面板增加「表情管理」tab
│   ├── 可上传自定义表情图片
│   ├── 可为表情绑定触发词/场景
│   └── 可删除/替换默认表情
└── 前后端存储
    ├── character_stickers 表（SQLite）：存储表情URL+触发词+角色
    ├── 表情图片存 uploads/stickers/ 目录
    └── API: GET/POST/DELETE /api/stickers/{character_name}
```

**实现时机**: P3 之后，与 P4 工具市场并行

### P3: 角色主动发消息 + 对话超时反应

- 角色可以主动发起对话，不只是在聊天中被动回复
- 主动触发：根据条件概率矩阵、时间间隔、话题关联度
- 例如春日发现有趣的事 → 主动@你；长门检测到资讯异常 → 发消息提醒
- **对话暂停/超时**：用户长时间不回复（如30分钟+），角色根据性格做出不同反应
  - 春日：抱怨「喂！人呢？！」「你到底有没有在听我说话！」
  - 阿虚：「……算了，反正你也不会回」
  - 长门：沉默观察，可能在长时间无响应后发一条简短询问
  - 朝比奈：「那个……你还好吗……？」
  - 古泉：「呵呵，看来你有别的事要忙呢」
- 后端需要新增定时/事件触发的消息推送机制

### P4: 工具市场（远期规划）

- 用户可以上传/下载自定义工具
- 工具接口规范：
  ```
  ToolSchema:
    id: string
    name: string
    icon: string
    desc: string
    prompt: string    // LLM调用时的system prompt
    author: string
    version: string
  ```
- 前端ToolList从API拉取工具列表（当前硬编码→API驱动）
- 用户可管理已安装/上传的工具
- 后端提供工具CRUD API + 下载/安装接口

#### 工具计划

| 工具         | 图标 | 说明                             |
| ------------ | ---- | -------------------------------- |
| 反无聊审查器 | 🔍   | 分析待办清单，区分真该做和拖延的 |

把时间规划融进反无聊审查器，由春日接管

反无聊审查器本身就在做“区分真该做和拖延”这件事，时间紧迫感正好能强化它的价值。你可以让它在原有基础上加一个模式：输入你的所有任务和截止日期，春日用她那种急躁但高效的方式，帮你排出一个“不按四象限，但绝对让你动起来”的顺序。她不会画标准的矩阵，而是直接告诉你“这个后天截止你还在这儿发呆？先做这个！那个虽然重要但还有两周，扔一边去，别拿来骗自己。”

这比标准的四象限更有冲击力，因为是春日式的鞭策，不是冷冰冰的优先级标签。你每次打开这个工具，就像被她揪着领子看了一眼你的待办清单，然后被她一顿输出。输出的内容里自然就隐含了重要性和紧迫性的判断，只是表达方式变成了“现在立刻马上”或者“那个以后再说”。

春日生命力雷达

定位不是心理健康工具，而是一个强制链接你内在冲动的“扫描仪”。它的逻辑分三层：

第一层：识别你今天的“能量泄漏点”
输入你今天做了什么事、想了什么念头，或者干脆什么都不输入，工具会主动问你：过去三小时里，哪一刻你觉得自己像行尸走肉？哪一刻你内心骂了一句脏话？春日会直接挑出你描述中那些“忍耐了不该忍的事”“说了违心的话”“明明不想做却还是做了”的瞬间。她用词会很尖锐，但目的不是责备，是让你看清自己今天把生命力耗在了什么地方。

第二层：找回你的“微小逆反”
分析完之后，她不会让你休息或放松，而是给你一个微型任务。这个任务极小，比如“去把桌上那个你忍了三天的文件扔到一边”“对那个让你不爽的人说‘不行’”“现在就站起来，做五个开合跳，纯粹因为你想。”任务的核心是让你做出一个完全出于自己意志的动作，切断那种被动应付一切的麻木感。任务完成，你会有一瞬间的掌控感回来。

第三层：保存你的“反死感证据”
每次完成一个小逆反，她会让你用一句话记下来，存进一个只有你能看到的“SOS团活力档案”。日后你再次感觉死感袭来，打开档案一看，全是过往“我还能这样”的证据。这些记录不是鸡汤，是事实，是你自己曾经冲破麻木的锚点。

行为特征
全程春日语气：不耐烦、热烈、拒绝任何自怜。她不会说“一切都会好”，而是说“别躺着，起来搞点事，哪怕是用勺子敲碗。”你觉得压力大，她的解决方案永远是先做一个你完全自主的决定，无论大小。生命力不是被安慰回来的，是被行动拽回来的。

阿虚反鸡汤净化器

输入任何一句励志语录、成功学废话、朋友圈正能量，阿虚帮你拆穿它，用吐槽的方式告诉你这句话为什么不靠谱、说话的人可能在回避什么。不只是娱乐，而是帮你建立一种免疫力，以后看到类似的话不会下意识觉得“我是不是不够努力”。压力和焦虑有很大一部分来自这种隐形对比，能把它消解掉，心态会稳很多。还有想办法帮用户环节焦虑怎么样. 比如我其实就是人工智能专业的,世界发展太快,专业也发展太快, 我常常怕被丢下,害怕落后,我希望有一个这种工具.

朝比奈喝茶工具.
没啥用, 就是单纯的朝比奈通知你要喝茶了, 提示喝水这样的?后边会加入音乐和动画播放接口吧,播放一个倒茶动画, 做成那种小闹钟吧! 就是用户定时啥时候要喝水?你考虑一下.后面我会给你小动画,和音乐,现在先留下接口即可

长门看书.
这个就是自习室.后面会有白噪音,也是有视频动画,美悠里的悠闲时光这样. 不过目前还没有视频动画和白噪音,你做了留一个这种的接口就行,允许用户上传文件,后面我会给你默认值让你引用.

### P5: 桌面打包（远期规划）

- Electron → Tauri 迁移
- 打包为独立桌面应用
- 内置 SQLite 数据库 + 本地 LLM 或 API Key 配置

## 角色 SKILL 概览

| 角色         | 心智模型 | SKILL.md 位置                        |
| ------------ | -------- | ------------------------------------ |
| 凉宫春日     | 4 个     | `skills/characters/haruhi/SKILL.md`  |
| 阿虚         | 5 个     | `skills/characters/kyon/SKILL.md`    |
| 长门有希     | 5 个     | `skills/characters/nagato/SKILL.md`  |
| 朝比奈实玖瑠 | 4 个     | `skills/characters/asahina/SKILL.md` |
| 古泉一树     | 5 个     | `skills/characters/koizumi/SKILL.md` |

每角色含 `references/research/01-07.md` 7 篇研究笔记。

## 数据驱动

| 数据           | 来源               | 用途           |
| -------------- | ------------------ | -------------- |
| 条件概率矩阵   | 全13卷小说对话统计 | 各角色接话概率 |
| 对象别语气调整 | addressee 关系矩阵 | 语气偏移       |
| 791条标注对话  | 手工标注           | 风格化参考     |
