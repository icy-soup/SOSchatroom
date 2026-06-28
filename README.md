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

## 功能一览

| 功能 | 说明 |
|------|------|
| 💬 单人聊天 | 与任意角色一对一交流 |
| 🏠 SOS团群聊 | 所有角色同时在线回复 |
| 🎭 角色扮演 | 选择扮演的角色与 AI 互动 |
| ✨ 风格化 | 输入自动转换为角色口吻，独立预览面板 |
| 🎬 场景设置 | 自定义对话背景和出席角色 |
| ✏️ 角色编辑 | 自定义头像/名称/签名/行为参数 |
| ⚡ 春日行动引擎 | 待办排序，春日式"现在立刻马上" |
| 📡 春日生命力雷达 | 能量泄漏扫描 + 逆反任务 + 活力档案 |
| 🧹 阿虚反鸡汤净化器 | 拆穿鸡汤，缓解焦虑 |
| 🍵 朝比奈喝茶工具 | 倒计时喝水提醒，动画占位 |
| 📖 长门看书 | 自习室，浮动计时器+自定义背景+白噪音占位 |
| 🌙 深色模式 | 左栏底部切换，持久化 |

## 项目结构

```
├── backend/                     # FastAPI + WebSocket 后端
│   ├── main.py                  # 服务入口、LLM、WebSocket、REST API
│   ├── database.py              # SQLite 持久化层
│   ├── config.py                # 角色映射、SKILL 加载
│   ├── tools/                   # 工具注册表（自动扫描根目录 tools/）
│   │   └── registry.py
│   ├── character_agent.py         # 多 Agent：每个角色独立决策+回复
│   └── engine/                    # 响应引擎
│       ├── trigger.py             #   概率矩阵加载
│       ├── character.py           #   system prompt 构建
│       └── style.py               #   对象别语气调整
├── frontend/                    # React + TypeScript + Vite 前端
│   └── src/
│       ├── components/          #   UI 组件（ChatArea、InputArea 等）
│       ├── hooks/               #   useWebSocket
│       ├── tools/               #   工具运行框架
│       │   ├── types.ts         #   接口规范
│       │   ├── registry.ts      #   import.meta.glob 自动扫描
│       │   ├── llm-view.tsx     #   LLM 工具通用界面
│       │   └── storage.ts       #   工具历史 localStorage
│       └── api.ts               #   REST API 客户端
├── tools/                       # ← 工具目录，drop-in 式
│   ├── action-engine/           #   definition.ts + prompt.txt
│   ├── vitality-radar/
│   ├── anti-inspiration/
│   ├── tea-timer/               #   + component.tsx
│   └── study-room/              #   + component.tsx
├── skills/characters/           # 5 个角色 SKILL.md
├── data/                        # 小说、标注对话、分析、脚本
├── docs/                        # 文档
│   └── README.md                #   文档索引
├── chatroom.bat                 # Windows 一键启动
└── chatroom.sh                  # Linux/Mac 一键启动
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

## 5 角色 SKILL

| 角色 | 心智模型 | SKILL 位置 |
|------|---------|-----------|
| 凉宫春日 | 4 个 | `skills/characters/haruhi/SKILL.md` |
| 阿虚 | 5 个 | `skills/characters/kyon/SKILL.md` |
| 长门有希 | 5 个 | `skills/characters/nagato/SKILL.md` |
| 朝比奈实玖瑠 | 4 个 | `skills/characters/asahina/SKILL.md` |
| 古泉一树 | 5 个 | `skills/characters/koizumi/SKILL.md` |

## 工具系统规范

新建工具只需三步：

1. 在 `tools/<id>/` 下创建 `definition.ts` + `prompt.txt`
2. `definition.ts` 引用 `../../frontend/src/tools/types` 类型
3. 控件型工具再加一个 `component.tsx` 组件

重启即用，无需修改任何配置文件。

> 调研日期：2026-05-23 | 基于《凉宫春日》系列全13卷原文
