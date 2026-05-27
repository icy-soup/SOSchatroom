# haruhi-skill

**SOS团聊天室** — 基于《凉宫春日》全13卷小说原文的多角色 AI 聊天室。
5 名角色（春日/阿虚/长门/朝比奈/古泉），真实对话数据驱动的响应引擎。

## 快速开始

```bash
# 一键启动（构建前端 + 启动后端）
.\chatroom.bat

# 或分步：
cd backend && pip install -r requirements.txt
cd ../frontend && npm install && npx vite build
cd ../backend && python main.py
```

访问 `http://localhost:8000`，右上角 ⚙ 配置 API Key。

## 项目结构

```
├── backend/                     # FastAPI + WebSocket 后端
│   ├── main.py                  # 服务入口、LLM 调用、WebSocket 路由
│   ├── config.py                # 角色映射、SKILL 加载
│   ├── engine/                  # 三层响应引擎
│   │   ├── trigger.py           #   触发层：谁应该回复
│   │   ├── character.py         #   角色层：system prompt 构建
│   │   └── style.py             #   风格层：对象别语气调整
│   └── requirements.txt
├── frontend/                    # React + TypeScript + Vite 前端
│   └── src/
│       ├── components/          #   ChatArea, InputArea, Sidebar, ...
│       ├── hooks/               #   useWebSocket
│       └── App.tsx
├── skills/characters/           # 5 个角色 SKILL.md
├── data/                        # 小说、标注对话、分析、脚本
│   └── scripts/                 #   对话挖掘与分析脚本
├── docs/                        # 文档
│   └── README.md                #   文档索引
└── chatroom.bat                 # Windows 一键启动
```

## 响应引擎三层架构

```
触发层 (trigger.py)  ── @提及/提问/概率roll，基于真实小说统计数据
    ↓
角色层 (character.py) ── 加载 SKILL.md → 构建 system prompt
    ↓
风格层 (style.py) ── 根据说话对象调整语气（基于addressee关系矩阵）
    ↓
LLM 调用 ── Anthropic/OpenAI 双协议，失败→演示模式兜底
```

## 5 角色 SKILL

| 角色 | 心智模型 | SKILL 位置 |
|------|---------|-----------|
| 凉宫春日 | 4 个 | `skills/characters/haruhi/SKILL.md` |
| 阿虚 | 5 个 | `skills/characters/kyon/SKILL.md` |
| 长门有希 | 5 个 | `skills/characters/nagato/SKILL.md` |
| 朝比奈实玖瑠 | 4 个 | `skills/characters/asahina/SKILL.md` |
| 古泉一树 | 5 个 | `skills/characters/koizumi/SKILL.md` |

调研笔记见 `docs/research/{角色}/`。

## 数据驱动

| 数据 | 来源 | 用途 |
|------|------|------|
| 条件概率矩阵 | 全 13 卷小说对话统计 | 上一位说话后各角色接话概率 |
| 对象别语气调整 | addressee 关系矩阵 | 说话对象不同时的语气偏移 |
| 791 条标注对话 | 手工标注 | 风格化训练参考 |

> 调研日期：2026-05-23 | 基于《凉宫春日》系列全13卷原文
