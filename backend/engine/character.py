"""Character Engine — load SKILL.md, build prompts, call LLM."""

from pathlib import Path
from config import PROJECT_ROOT, CHARACTER_DIR_MAP

SKILL_DIR = PROJECT_ROOT / "skills" / "characters"


def load_skill(name: str) -> str:
    """Load a character's SKILL.md content."""
    dir_name = CHARACTER_DIR_MAP.get(name)
    if not dir_name:
        return ""
    skill_path = SKILL_DIR / dir_name / "SKILL.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8")


def build_system_prompt(name: str) -> str:
    """Build the full system prompt with SKILL + output rules.

    Character identity and conversation history are carried by the messages
    array (each content prefixed with 【character】), NOT in the system prompt.
    This avoids the LLM learning the prefix format from in-context examples.
    """
    skill = load_skill(name)

    parts = [
        f"你是{name}。请完全以{name}的身份和语气回应。",
        f"角色设定：\n{skill}",
        (
            "回复规则：\n"
            "1. 只说【你自己】的台词，不要替其他角色说话——你不是他们\n"
            "2. 参考对话历史，围绕当前话题展开回复，不要每句都跳到全新的话题\n"
            "   可以适当发散，但先接住对方上一句话再展开\n"
            "3. 直接输出，不要加任何前缀。以下格式都是错误的：\n"
            "   - 错误：凉宫春日：今天天气真好\n"
            "   - 错误：【凉宫春日】今天天气真好\n"
            "   - 错误：凉宫春日: 今天天气真好\n"
            "   - 错误：—今天天气真好\n"
            "   - 正确：今天天气真好\n"
            "4. 输入消息中的【角色名】格式只是标注谁在说话，不要模仿——你的输出不需要任何标注\n"
            "5. 每条回复不超过200字\n"
            "6. 说人话，不要翻译腔\n\n"
            f"你是{name}，不是其他角色。只输出{name}会说的话。"
        ),
    ]

    return "\n\n".join(parts)


def build_conversation_context(history: list[dict], max_turns: int = 20) -> list[dict]:
    """Build conversation messages with character identity in content.

    Each message is prefixed with 【character】 so the LLM knows who spoke.
    The system prompt explicitly warns not to mimic this format in output.
    """
    messages = []
    for entry in (history[-max_turns:] if history else []):
        role = "assistant" if entry.get("is_bot") else "user"
        messages.append({
            "role": role,
            "content": f"【{entry['character']}】{entry['text']}",
        })
    return messages
