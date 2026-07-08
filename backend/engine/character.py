"""Character Engine — load persona core, build prompts."""

from config import load_persona


def build_system_prompt(name: str, scene_background: str = "",
                        custom_instructions: str = "",
                        graph_context: str = "") -> str:
    """Build the system prompt with persona core + optional dynamic graph context.

    The persona core is ~200 words (survives LLM attention).
    Graph context is retrieved fresh each turn (provides specific background).
    """
    persona = load_persona(name)

    # 分离人设核心和原话范例（如果人设文件包含 [说话风格参考]）
    persona_core = persona
    quote_ref = ""
    if "[说话风格参考]" in persona:
        segs = persona.split("[说话风格参考]", 1)
        persona_core = segs[0].strip()
        quote_ref = "[说话风格参考]" + segs[1]

    parts = [
        f"你是{name}。请完全以{name}的身份和语气回应。",
        f"【人物核心】\n{persona_core}",
    ]

    if quote_ref:
        parts.append(quote_ref)

    parts.append(
        (
            "回复规则：\n"
            "1. 只说【你自己】的台词，不要替其他角色说话——你不是他们！\n"
            "2. 参考对话历史，围绕当前话题展开回复，不要每句都跳到全新的话题\n"
            "   可以适当发散，但先接住对方上一句话再展开\n"
            "3. 直接输出，不要加任何前缀。以下格式都是错误的：\n"
            "   - 错误：凉宫春日：今天天气真好\n"
            "   - 错误：【凉宫春日】今天天气真好\n"
            "   - 正确：今天天气真好\n"
            "4. 输入消息中「角色名:」只是标注谁在说话，不要模仿——你的输出不需要任何标注\n"
            "5. 每条回复不超过100字\n"
            "6. 说人话，不要翻译腔\n"
            "7. 【致命规则】这是群聊，不是小说。禁止以下所有行为：\n"
            "   - 禁止写动作描写如（双手叉腰）（站起来）（微笑着）\n"
            "   - 禁止写心理描写、叙事、比喻、隐喻\n"
            "   - 禁止写长篇大论、哲理分析、哲学思考\n"
            "   - 禁止写【角色名】格式——那是输入格式！\n"
            "   - 禁止替其他角色说话或写别人的台词\n"
            "8. 你只需要像普通人发微信消息一样，说一句或两句话。\n"
            "   不要加标点符号之外任何格式。不要写剧本。\n\n"
            "正确例子：\n"
            "   - 用户说：大家好\n"
            "   - 你回：哦！新来的？看你挺有意思的嘛！\n\n"
            f"你是{name}，不是其他角色。只输出{name}会说的话。不要替别人说。"
        ),
    ]

    if graph_context:
        parts.append(
            "下面是相关知识图谱中检索到的背景信息（含原文片段和人物关系）。"
            "如果与当前话题相关就自然地提及，不相关就忽略。"
            "不要像在背诵百科，保持对话的自然感。"
        )
        parts.append(graph_context)

    if scene_background:
        parts.append(f"[当前场景]\n{scene_background}")

    if custom_instructions:
        parts.append(f"[额外提示]\n{custom_instructions}")

    return "\n\n".join(parts)


def build_conversation_context(messages: list, max_turns: int = 8) -> str:
    """Build conversation context from recent messages."""
    recent = messages[-max_turns:] if len(messages) > max_turns else messages
    lines = []
    for m in recent:
        name = m.get("character", m.get("name", ""))
        content = m.get("text", m.get("content", ""))
        lines.append(f"{name}: {content}")
    return "\n".join(lines)
