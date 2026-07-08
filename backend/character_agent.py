"""Character Agent — 每个角色独立的消息处理单元。"""

import random
import re as re_module
from typing import Optional, Callable

from config import load_persona
from database import get_character_config
from engine.character import build_system_prompt, build_conversation_context
from engine.style import build_style_instruction
from graphrag.retriever import GraphRetriever


class CharacterAgent:
    """单个角色的 Agent 实例。

    每个 Agent 拥有：
    - 独立的 message_log
    - 独立的 API 配置（key/url/model/temperature）
    - 独立的回复决策逻辑
    """

    def __init__(
        self,
        name: str,
        session: dict,
        call_llm_func: Callable,
        get_demo_func: Callable,
        sanitize_func: Callable,
        broadcast_func: Callable,
        graph_id: str = "",
    ):
        self.name = name
        self.session = session
        self.message_log: list[dict] = []

        # 外部函数注入（避免循环 import main.py）
        self._call_llm = call_llm_func
        self._get_demo = get_demo_func
        self._sanitize = sanitize_func
        self._broadcast = broadcast_func

        # GraphRAG 图谱检索器（容错：图不存在时静默跳过）
        self._retriever = None
        if graph_id:
            try:
                self._retriever = GraphRetriever(graph_id)
            except Exception as e:
                print(f"[character_agent] GraphRetriever 初始化失败({name}, {graph_id}): {e}")

        self._load_config()

    def _load_config(self):
        """从多层配置源加载角色的 API 配置。
        优先级：会话 > DB > 文件配置 > 全局默认
        """
        char_cfg = self.session.get("character_api_config", {}).get(self.name, {})
        db_cfg = get_character_config(self.name) or {}

        self.api_key = (char_cfg.get("api_key")
                       or db_cfg.get("api_key")
                       or self.session.get("api_key", ""))
        self.api_url = (char_cfg.get("api_url")
                       or db_cfg.get("api_url")
                       or self.session.get("api_url", ""))
        self.model = (char_cfg.get("model")
                     or db_cfg.get("model")
                     or self.session.get("model", ""))
        self.temperature = db_cfg.get("temperature", 0.8)

    async def observe_and_reply(self, message: dict, novel_probs: dict) -> Optional[dict]:
        """观察消息，决定是否回复，若回复则生成并广播。

        Args:
            message: {"character": str, "text": str, "is_bot": bool}
            novel_probs: 概率表 {responder: prob}（get_character_probs 返回的平坦 dict）

        Returns:
            回复 dict {"type": "message", "character": ..., "text": ..., "is_bot": True}
            或 None（不回复）
        """
        # 1. 追加到自己的 message_log
        self.message_log.append(message)

        # 2. 不回复自己的消息
        if message["character"] == self.name:
            return None

        # 3. 独立决策（双层：LLM 判断 + 概率兜底）
        if not await self._should_respond(message, novel_probs):
            return None

        # 4. 生成回复
        return await self._generate_reply(message)

    async def _should_respond(self, message: dict, novel_probs: dict) -> bool:
        """双层决策：LLM 判断相关度 + 概率兜底插嘴。"""
        # @提及 → 强制回复
        for word in [self.name, self.name[:2]]:
            if f"@{word}" in message["text"]:
                return True

        # Layer 1: LLM 快速判断相关度
        relevance = await self._judge_relevance(message)

        # 高度相关（>=70）→ 直接回复
        if relevance >= 70:
            return True

        # 中度相关（30-69）→ 按比例调概率
        if relevance >= 30:
            base_prob = novel_probs.get(self.name, 0.15)
            adjusted = base_prob * (relevance / 30)
            return random.random() < adjusted

        # 低度相关（<30）→ 概率 roll 是否插嘴
        return self._roll_for_interjection(message, novel_probs)

    async def _judge_relevance(self, message: dict) -> int:
        """用 LLM 快速判断消息跟自己的相关度，返回 0-100。"""
        # 最近 3 条消息做上下文
        recent = self.message_log[-3:]
        context_lines = [f"{m['character']}: {m['text'][:80]}" for m in recent]
        context_str = "\n".join(context_lines)

        system = (
            f"你是{self.name}。判断这条消息是否跟你有关系。只输出数字。"
        )

        user_msg = (
            f"最近的对话：\n{context_str}\n\n"
            f"新消息——{message['character']}说：{message['text']}\n\n"
            f"相关度 (0-100)："
        )

        result = await self._call_llm(
            self.api_key, self.api_url, self.model,
            system, [{"role": "user", "content": user_msg}],
        )

        if result is None:
            return 50

        match = re_module.search(r'(\d+)', result)
        return min(100, max(0, int(match.group(1)))) if match else 50

    def _roll_for_interjection(self, message: dict, novel_probs: dict) -> bool:
        """低相关度时，概率决定是否插嘴。"""
        base_prob = novel_probs.get(self.name, 0.15)
        adjusted = base_prob * 1.5
        if not message.get("is_bot"):
            adjusted += 0.10
        adjusted = min(adjusted, 0.30)  # 封顶 30%
        return random.random() < adjusted

    async def _generate_reply(self, message: dict) -> Optional[dict]:
        """调用 LLM 生成回复。"""
        # 广播思考中
        await self._broadcast({
            "type": "thinking",
            "character": self.name,
        })

        try:
            # 图谱检索（容错：失败时静默跳过）
            graph_context = ""
            if self._retriever:
                try:
                    graph_context = self._retriever.retrieve(
                        message.get("text", ""),
                        character=self.name,
                        max_nodes=6,
                        max_edges=10,
                        max_episodes=2,
                    )
                except Exception as e:
                    print(f"[character_agent] 图谱检索失败({self.name}): {e}")

            # 构建 system prompt
            custom_instructions = self.session.get(
                "character_api_config", {}
            ).get(self.name, {}).get("custom_instructions", "")

            system_prompt = build_system_prompt(
                self.name,
                scene_background=self.session.get("scene_background", ""),
                custom_instructions=custom_instructions,
                graph_context=graph_context,
            )

            # 明确告知角色在和谁对话
            user_char = message["character"]
            system_prompt += f"\n\n当前和你对话的是{user_char}。请直接对{user_char}说话。"
            system_prompt += "\n\n【重要】每次回复严格控制在100字以内。简明扼要，像真正的对话一样。如果你写太多系统会自动截断，所以只说最必要的话。"

            style_instruction = build_style_instruction(
                self.name, message["character"]
            )
            if style_instruction:
                system_prompt += f"\n\n{style_instruction}"

            # 构建 context
            ctx = build_conversation_context(self.message_log)

            # 在对话历史最后加一个简短提醒（对抗 prompt 衰减）
            persona = load_persona(self.name)
            # 从人设中提取精简版提醒（前 50 字 + 知识边界）
            reminder = f"【角色提醒】你是{self.name}。"
            if "[知识边界]" in persona:
                bounds = persona.split("[知识边界]")[1].strip()
                # 取前 2 条知识边界
                bound_lines = [l.strip() for l in bounds.split("\n") if l.strip() and not l.startswith("[")]
                if bound_lines:
                    reminder += "\n牢记：你不知道的事——" + "；".join(bound_lines[:2])
            # 用单独的一条 user message 传递提醒，紧挨 LLM 输出位置
            messages_for_llm = [
                {"role": "user", "content": ctx},
                {"role": "user", "content": reminder},
            ]

            # 调用 LLM（用自己的 API 配置）
            reply = await self._call_llm(
                self.api_key, self.api_url, self.model,
                system_prompt, messages_for_llm,
            )

            if reply is None:
                reply = self._get_demo(self.name, message["text"])
            else:
                reply = self._sanitize(reply)

            # 截断过长的回复（保留完整句子）
            MAX_LEN = 150
            if len(reply) > MAX_LEN:
                # 在 MAX_LEN 范围内找最后一个句号/感叹号/问号
                trimmed = reply[:MAX_LEN]
                last_end = max(trimmed.rfind('。'), trimmed.rfind('！'),
                               trimmed.rfind('？'), trimmed.rfind('……'))
                if last_end > MAX_LEN // 2:
                    reply = reply[:last_end + 1]
                else:
                    reply = trimmed + '……'

            # 追加到日志
            bot_msg = {"character": self.name, "text": reply, "is_bot": True}
            self.message_log.append(bot_msg)
            self.session["message_log"].append(bot_msg)
            self.session["last_speaker"] = self.name

            return {
                "type": "message",
                "character": self.name,
                "text": reply,
                "is_bot": True,
            }
        finally:
            # 清除思考中
            await self._broadcast({
                "type": "thinking_clear",
                "character": self.name,
            })

    def restore_log(self, messages: list[dict]):
        """从 DB 恢复消息到 agent 的独立 message_log。"""
        self.message_log = [
            {"character": m["role"], "text": m["content"], "is_bot": bool(m["is_bot"])}
            for m in messages
        ]
