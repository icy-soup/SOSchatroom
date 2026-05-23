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


def build_system_prompt(name: str, conversation_history: list[dict]) -> str:
    """Build the full system prompt with SKILL + conversation transcript embedded.

    Speaker info is embedded here (in the system prompt) rather than in the
    messages content, to prevent the LLM from mimicking any format prefix.
    """
    skill = load_skill(name)

    # Embed conversation transcript in the system prompt itself
    transcript = ""
    if conversation_history:
        lines = []
        for entry in conversation_history[-8:]:
            lines.append(f"【{entry['character']}】{entry['text']}")
        transcript = "\n".join(lines)

    parts = [
        f"你是{name}。请完全以{name}的身份和语气回应。",
        f"角色设定：\n{skill}",
    ]
    if transcript:
        parts.append(f"对话记录：\n{transcript}")
    parts.append(
        "回复规则：\n"
        "1. 只说【你自己】的台词，不要替其他角色说话——你不是他们\n"
        "2. 直接说话，不要加任何前缀（包括【角色名】、角色名:、—等任何形式）\n"
        "3. 每条回复不超过200字\n"
        "4. 说人话，不要翻译腔\n\n"
        "你是{name}，不是其他角色。只输出{name}会说的话。"
    )

    return "\n\n".join(parts)


def build_conversation_context(history: list[dict], max_turns: int = 20) -> list[dict]:
    """Build conversation messages for the LLM API call.

    Speaker info is in the system prompt, NOT in message content.
    This prevents the LLM from learning to prefix responses with a speaker tag.
    """
    messages = []
    for entry in history[-max_turns:]:
        role = "assistant" if entry.get("is_bot") else "user"
        messages.append({"role": role, "content": entry["text"]})
    return messages
