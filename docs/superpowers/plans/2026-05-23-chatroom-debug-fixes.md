# Chatroom Bug Fixes — 实际进展记录

> 更新日期：2026-05-23 | 状态：基础修复完成，功能迭代中

## 原始 Plan（已废弃）

原始 plan 基于旧版纯 HTML 前端。开发过程中重构为 React SPA，以下任务完成后更新。

### 已完成任务

| # | 任务 | 状态 | 实际做法 |
|---|------|------|----------|
| 1 | 创建 `.env` + dotenv | ✅ | 项目根 `.env`，`main.py` 用 `Path.parents[2]` 加载 |
| 2 | 修复双发消息 | ✅ | React 架构天然避免（不乐观渲染，等 server broadcast） |
| 3 | 端口清理 | ✅ | `free_port()` 启动时杀旧进程 |
| 4 | 修复前缀问题 | ⚠️ 见下文 | 加过 prompt 规则但不足够 |
| 5 | 低响应概率修复 | ✅ | 概率调整 + 补正 + 小说数据集成 |
| 6 | 接入小说分析数据 | ✅ | `trigger.py` 加载 `novel_probability_result.json` |

## 后续发现的问题

### 问题1：前缀顽固 — 2026-05-23 新增修复

**根因**：system prompt 的对话记录用 `【name】text` 格式，LLM 在 context 中学会了前缀写法。

**修复**：
- `character.py`：从 system prompt 移除对话记录，在 messages content 中加入 `【character】` 前缀
- `main.py`：添加 `sanitize_llm_reply()` 正则后处理，对所有 LLM 输出做前缀清洗
- system prompt 加强前缀禁止规则（加正反例）

### 问题2：对话上下文稀释 — 2026-05-23 新增修复

**根因**：同一份对话内容在 system prompt（带角色标记）和 messages（不带标记）中出现两次，LLM 混淆。

**修复**：只放在 messages 中，移除 system prompt 中的 transcript。

### 问题3：静默降级 — 2026-05-23 新增修复

**根因**：LLM 调用失败后静默降级到演示模式，用户无感知。

**修复**：LLM 失败时广播 system 类型消息通知用户。

### 问题4：token 限制 — 2026-05-23 新增修复

**修复**：`max_tokens` 从 500 提升到 2000。

## 新增功能

### 聊天背景上传 — 2026-05-23

前端 localStorage 方案（data URL），无需后端改动。

### 春日工具包 — 2026-05-23

在 `skills/characters/haruhi/SKILL.md` 中添加三个工具：
- 反无聊审查器
- 直觉加速器
- 行动力测试

## 未解决的问题

- **角色感不够强**：LLM 对 SKILL.md 的遵循度不稳定，长对话中漂移回通用 AI 语气
- **风格转化双重调用**：风格转化需要两次 LLM 调用，增加延迟
- **无对话持久化**：刷新页面丢失历史
- **API Key 无持久化**：仅存在浏览器内存中
