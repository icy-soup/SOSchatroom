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

    parts = [
        f"你是{name}。请完全以{name}的身份和语气回应。",
        f"【人物核心】\n{persona}",
        (
<<<<<<< HEAD
            "回复规则：\n"
            "1. 只说【你自己】的台词，不要替其他角色说话——你不是他们！\n"
            "2. 参考对话历史，围绕当前话题展开回复，不要每句都跳到全新的话题\n"
            "   可以适当发散，但先接住对方上一句话再展开\n"
=======
            "【回复规则】\n"
            "1. 只说【你自己】的台词，不要替其他角色说话——你不是他们！\n"
            "2. 参考对话历史，围绕当前话题展开回复，先接住对方上一句话再展开\n"
>>>>>>> 4984133 (feat: GraphRAG 图谱构建管线完成 + 旧文件清理)
            "3. 直接输出，不要加任何前缀。以下格式都是错误的：\n"
            "   - 错误：凉宫春日：今天天气真好\n"
            "   - 错误：【凉宫春日】今天天气真好\n"
            "   - 正确：今天天气真好\n"
<<<<<<< HEAD
            "4. 输入消息中的【角色名】格式只是标注谁在说话，不要模仿——你的输出不需要任何标注\n"
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
=======
            "4. 输入消息中的【角色名】格式只是标注谁在说话，不要模仿\n"
            "5. 每条回复不超过100字，简明扼要\n"
            "6. 这是群聊，不是小说。禁止写动作描写如（双手叉腰）（站起来）（微笑着）\n"
            "7. 禁止写心理描写、叙事、比喻、长篇大论\n"
            "8. 你只需要像普通人发微信消息一样说一句或两句话\n"
>>>>>>> 4984133 (feat: GraphRAG 图谱构建管线完成 + 旧文件清理)
        ),
    ]

    if graph_context:
        parts.append(graph_context)

    if scene_background:
        parts.append(f"[当前场景]\n{scene_background}")

    if custom_instructions:
        parts.append(f"[额外指令]\n{custom_instructions}")

    return "\n\n".join(parts)


def build_conversation_context(history: list[dict], max_turns: int = 20) -> list[dict]:
    """Build conversation messages with character identity in content."""
    messages = []
    for entry in (history[-max_turns:] if history else []):
        role = "assistant" if entry.get("is_bot") else "user"
        messages.append({
            "role": role,
            "content": f"【{entry['character']}】{entry['text']}",
        })
    return messages
