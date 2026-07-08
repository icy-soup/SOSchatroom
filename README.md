# SOSchatroom — 凉宫春日 AI 聊天室

基于《凉宫春日》全 13 卷小说原文的多角色 AI 聊天室。
5 名角色，GraphRAG 图谱驱动的动态上下文引擎。

## 前置要求

- **Python** 3.10+
- **Node.js** 18+（构建前端用）
- **npm**（随 Node.js 自带）

## 快速开始

```bash
# Windows
scripts/chatroom.bat

# 或手动启动
cd backend && python main.py       # 后端 :8000
cd frontend && npx vite            # 前端 :5173
```

访问 `http://localhost:5173` 开始聊天。

图谱构建服务器独立运行于 `http://localhost:8001`（`scripts/start_graphrag.bat`）。

## 功能

| 功能 | 说明 |
|------|------|
| 💬 多人群聊 | 与 5 名角色群聊，串行 dispatch 自然流转 |
| 🎭 角色扮演 | 选择扮演的角色与 AI 互动 |
| ✨ 风格化 | 输入自动转换为角色口吻 |
| 🎬 场景设置 | 自定义对话背景和出席角色 |
| 🕸️ 知识图谱 | 从小说原文自动提取实体关系，D3.js 可视化 |
| 🔍 图谱检索 | 每轮对话从图谱检索相关背景 + 原文段落 |
| 📋 人设生成 | 从图+原文混合生成，含说话风格例句 + 知识边界 |

## 项目结构

```
backend/
├── main.py                 # 聊天室服务（FastAPI :8000）
├── server_graphrag.py      # 图谱构建服务（FastAPI :8001）
├── character_agent.py      # 角色 Agent（图谱检索 + LLM 调用）
├── graphrag/               # 图谱构建管线
│   ├── store.py            # SQLite 图存储（4 表 + episodes）
│   ├── builder.py          # LLM 提取 + 别名消解 + 增量构建
│   └── retriever.py        # 双通道检索（图关系 + 原文段落）
├── engine/                 # 对话引擎
│   ├── character.py        # System Prompt 构建
│   ├── trigger.py          # 回复决策（@mention / 提问 / 概率）
│   └── style.py            # 语气调整
├── personas/               # 角色人设（图+原文混合生成）
├── templates/graphrag_build.html  # 图谱前端
└── scripts/
    └── generate_persona.py # 人设生成脚本
frontend/                   # React + TypeScript 聊天室前端
data/graphs/haruhi_novel.db # 图谱（461节点 / 1344边 / 381episodes）
scripts/                    # 运维脚本（.bat）
```

## 对话架构

```
用户消息
  → select_responders 规则评分（@mention > 提问 > 概率 > 话题匹配）
  → 选最高分角色回复
      → retriever 双通道检索（图关系 + 原文段落）
      → build_system_prompt（人设 + 原话例句 + 知识边界 + 检索结果）
      → call_llm → 返回回复
  → 检测 @mention → 触发跟随回复（最多 1 个）
```

