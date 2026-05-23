# SOS团聊天室

凉宫春日系列全角色 AI 聊天室。基于全 13 卷小说对话数据构建的响应引擎，支持 5 名角色同时在线对话。

## 功能

- **5 名可玩角色**：凉宫春日、阿虚、长门有希、朝比奈实玖瑠、古泉一树
- **AI 自动回复**：基于 SKILL.md 的角色 prompt + 可选 LLM 后端（DeepSeek / Anthropic）
- **小说数据驱动**：回复概率、对象别语气均基于原作对话统计分析
- **双模式**：API Key 模式（LLM 生成） / 演示模式（硬编码回复）
- **风格转化**：输入普通文本 → AI 转化为角色语气
- **角色独立 API 配置**：每个角色可使用不同模型/后端
- **WebSocket 实时通信**：多客户端同步

## 快速开始

### 前置依赖

- Python 3.11+
- Node.js 18+（前端构建）
- （可选）API Key（DeepSeek / Anthropic）

### 启动

```bash
# 一键启动（构建前端 + 启动后端）
cd chatroom
.\chatroom.bat
```

或分步启动：

```bash
# 1. 安装后端依赖
cd chatroom/backend
pip install -r requirements.txt

# 2. 构建前端
cd ../frontend
npm install
npx vite build

# 3. 启动服务
cd ../backend
python main.py
```

访问 `http://localhost:8000`

### 配置 API

聊天室右上角 ⚙ → 设置 API Key / 地址 / 模型。

如使用本地 `.env`，在项目根目录创建：

```env
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_API_URL=https://api.deepseek.com
ANTHROPIC_MODEL=deepseek-v4-flash
```

## 技术架构

```
chatroom/
├── backend/           # FastAPI + WebSocket 后端
│   ├── main.py        # 服务入口、WebSocket 路由、LLM 调用
│   ├── config.py      # 角色映射、SKILL 加载
│   ├── engine/
│   │   ├── trigger.py    # 触发层：谁应该回复
│   │   ├── character.py  # 角色层：system prompt 构建
│   │   └── style.py      # 风格层：对象别语气调整
│   └── requirements.txt
├── frontend/          # React + TypeScript + Vite 前端
│   └── src/
│       ├── App.tsx
│       ├── components/   # ChatArea, InputArea, Sidebar,...
│       └── hooks/        # useWebSocket
└── chatroom.bat       # 一键启动脚本
```

### 响应引擎三层架构

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
  └─ 加载 addressee 关系数据
  └─ 根据说话对象调整语气
       ↓
LLM 调用 (main.py)
  └─ Anthropic SDK / OpenAI SDK 双协议支持
  └─ 调用失败 → 演示模式兜底
```

## 数据驱动

响应引擎基于 `data/chatroom/response_engine_config.json`，数据来源：

| 数据 | 来源 | 用途 |
|------|------|------|
| 条件概率矩阵 | 全13卷小说对话统计 | 上一位说话后各角色接话概率 |
| 基准语气 | addressee 分析 | 各角色默认语气（感叹比/提问比/敬语度等） |
| 对象别语气调整 | addressee 关系矩阵 | 说话对象不同时的语气偏移 |
| 核心话题映射 | 小说关键词提取 | 话题触发时的概率加成 |

## 已知问题 / 待改进

### LLM 回复质量
- **角色前缀问题**：AI 有时仍会输出「角色名:」前缀，system prompt 已加约束但未能完全消除
- **角色感不足**：LLM 对 SKILL.md 的遵循度不稳定，长对话中容易漂回通用 AI 语气
- **双重 LLM 调用**：风格转化功能需要两次 LLM 调用（转化 → 回复），增加延迟和成本
- **演示模式过于简陋**：硬编码回复太短太泛，无法体现角色差异

### 对话体验
- **串行回复**：多个角色回复时串行处理，后回复者能看到前者的回复，但总等待时间叠加
- **无对话持久化**：刷新页面丢失所有历史
- **连接状态不直观**：缺少显式的 WebSocket 连接指示器
- **错误处理静默**：LLM 调用失败后静默降级到演示模式，用户无感知

### 架构
- **API Key 无持久化**：仅存在浏览器内存中，刷新需重新配置
- **novel_probability_result.json 路径硬编码**：在 trigger.py 中写死，对项目结构变化敏感
- **对话历史在 system prompt 中**：放在 system 字段而非 messages 中，浪费 prompt cache
- **前端 build 产物在仓库中**：dist/ 目录被跟踪，应评估是否只构建不提交

### 安全
- ~~硬编码 API Key 已移除~~（原 main.py:102 的硬编码 key 已清除）
- `.env` 已加入 `.gitignore`，API Key 不会提交到仓库

## 计划 vs 实际

参考 `docs/superpowers/plans/2026-05-23-chatroom-debug-fixes.md`：

| 计划项 | 状态 | 差异说明 |
|--------|------|----------|
| dotenv 加载 | ✅ 完成 | 从项目根 `.env` 加载（非 plan 说的 `backend/.env`） |
| 修复双发消息 | ✅ 完成 | React 架构天然避免（不乐观渲染，等 server broadcast） |
| 端口清理 | ✅ 完成 | `free_port()` 启动时杀旧进程 |
| 修复前缀问题 | ⚠️ 部分解决 | 规则已加但 LLM 不完全服从，需更强约束 |
| 低响应概率修复 | ✅ 完成 | 概率调整 + 话题补正 + 小说数据集成 |
| 接入小说分析数据 | ✅ 完成 | trigger.py 加载真实 novel_probability_result.json |

## 许可

MIT
