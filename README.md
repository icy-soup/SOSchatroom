# haruhi-skill

**SOS团聊天室** — 基于《凉宫春日》全13卷小说原文的多角色 AI 聊天室。
5 名角色（春日/阿虚/长门/朝比奈/古泉），真实对话数据驱动的响应引擎。

## 前置要求

- **Python** 3.10+
- **Node.js** 18+（构建前端用）
- **npm**（随 Node.js 自带）

## 快速开始

```bash
# 1. 安装依赖
cd backend && pip install -r requirements.txt
cd ../frontend && npm install

# 2. 配置 API Key（可选，不配则走演示模式）
# 编辑 backend/.env，填入你的 API Key
# 支持：DeepSeek / OpenAI / Anthropic

# 3. 启动
# 方式一：双击 chatroom.bat（Windows）
# 方式二：bash chatroom.sh（Linux/Mac）
# 方式三：手动启动
cd backend && python main.py &     # 后端 :8000
cd frontend && npx vite            # 前端 :5173
```

访问 `http://localhost:5173` 即可开始聊天。

图谱构建服务器独立运行于 `http://localhost:8001`。

## 功能一览

| 功能 | 说明 |
|------|------|
| 💬 单人聊天 | 与任意角色一对一交流 |
| 🏠 SOS团群聊 | 所有角色同时在线回复 |
| 🎭 角色扮演 | 选择扮演的角色与 AI 互动 |
| ✨ 风格化 | 输入自动转换为角色口吻，独立预览面板 |
| 🎬 场景设置 | 自定义对话背景和出席角色 |
| ✏️ 角色编辑 | 自定义头像/名称/签名/行为参数 |
| 🌙 深色模式 | 左栏底部切换，持久化 |
| 🕸️ 知识图谱构建 | 从小说原文自动提取实体和关系，D3.js 力导向图可视化 |
| 📋 多图谱管理 | 图谱切换 / 备份另存 / 构建确认 / 节点隐藏持久化 |
| 🎯 图谱编辑 | 节点隐藏/恢复/删除，手动增删关系，LLM 辅助实体合并 |
| 🔍 图谱检索增强（待接入） | 对话时从图谱检索相关上下文注入 LLM |

## 项目结构

```
├── backend/                        # Python 后端
│   ├── main.py                     # 聊天室 API + WebSocket (:8000)
│   ├── server_graphrag.py          # 图谱构建独立服务器 (:8001)
│   ├── database.py                 # SQLite 对话历史
│   ├── config.py                   # 应用配置
│   ├── character_agent.py          # 多 Agent 角色引擎
│   ├── engine/                     # 响应引擎（trigger/character/style）
│   ├── graphrag/                   # GraphRAG 图谱构建管线
│   │   ├── builder.py             #   LLM 提取 + 别名消解 + 增量写入
│   │   ├── store.py               #   SQLite 图存储
│   │   └── retriever.py           #   对话时图谱检索
│   ├── templates/graphrag_build.html  # 图谱构建前端页面
│   ├── config/chatroom.json       # 运行时配置
│   └── scripts/                   # 后端 CLI 工具（build_graph / finalize_graph / dedup_graph）
├── frontend/                       # React + TypeScript + Vite 前端
│   └── src/
│       ├── components/           #   UI 组件
│       ├── hooks/                #   useWebSocket
│       ├── tools/                #   工具系统
│       └── api.ts                #   REST API
├── tools/                         # drop-in 工具目录
├── data/                          # 运行时数据
│   ├── novels/txt全卷.txt        #   凉宫春日全13卷原文
│   └── graphs/haruhi_novel.db    #   构建好的图谱（自动生成）
├── scripts/                       # 运维脚本
│   ├── chatroom.bat              #   聊天室一键启动
│   ├── start_graphrag.bat        #   图谱构建服务器启动
│   └── stop_graphrag.bat         #   图谱构建服务器停止
├── docs/                          # 文档
```

## 多 Agent 架构

```
用户消息 → 广播到所有独立 Agent

凉宫春日Agent:  独立 message_log → LLM 判断相关度 → 用自己的 API Key 调 LLM → 回复
阿虚Agent:      独立 message_log → LLM 判断相关度 → 用自己的 API Key 调 LLM → 回复
长门有希Agent:  独立 message_log → LLM 判断相关度 → 用自己的 API Key 调 LLM → 回复
朝比奈Agent:    独立 message_log → LLM 判断相关度 → 用自己的 API Key 调 LLM → 回复
古泉Agent:      独立 message_log → LLM 判断相关度 → 用自己的 API Key 调 LLM → 回复

每个 Agent：
- 独立决定是否回复（LLM 判断相关度 + 概率兜底插嘴）
- 独立 API Key / URL / Model
- 两轮对话：第一轮回用户，第二轮 agent 之间互相反应
- 真人小说对话数据（novel_probability_result.json）做参考概率
```

## 工具系统规范

新建工具只需三步：

1. 在 `tools/<id>/` 下创建 `definition.ts` + `prompt.txt`
2. `definition.ts` 引用 `../../frontend/src/tools/types` 类型
3. 控件型工具再加一个 `component.tsx` 组件

重启即用，无需修改任何配置文件。

> 调研日期：2026-05-23 | 基于《凉宫春日》系列全13卷原文
