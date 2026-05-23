"""Load response engine config and character SKILL files."""

import json
from pathlib import Path

# Project root (haruhi-skill/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "data" / "chatroom" / "response_engine_config.json"
SKILL_DIR = PROJECT_ROOT / "skills" / "characters"

# Character name mappings
CHARACTER_NAMES = ["凉宫春日", "阿虚", "长门有希", "朝比奈实玖瑠", "古泉一树"]
CHARACTER_DIR_MAP = {
    "凉宫春日": "haruhi",
    "阿虚": "kyon",
    "长门有希": "nagato",
    "朝比奈实玖瑠": "asahina",
    "古泉一树": "koizumi",
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_character_skill(name: str) -> str:
    """Load a character's SKILL.md as system prompt text."""
    dir_name = CHARACTER_DIR_MAP.get(name)
    if not dir_name:
        return ""
    skill_path = SKILL_DIR / dir_name / "SKILL.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8")


def build_system_prompt(name: str) -> str:
    """Build the full system prompt for a character."""
    skill = load_character_skill(name)
    return (
        f"你是{name}。请完全以{name}的身份和语气回应。\n\n"
        f"角色设定：\n{skill}\n\n"
        "注意：保持角色一致性，回应要符合角色的说话风格和性格特征。"
        "每次回复控制在200字以内。"
    )


CONFIG = load_config()


def get_character_api_config(name: str) -> dict:
    """Get per-character API override (may return empty dict if not configured)."""
    api_config = CONFIG.get("character_api_config", {})
    overrides = api_config.get(name, {})
    if not overrides:
        return {}
    return {
        "api_url": overrides.get("api_url"),
        "model": overrides.get("model"),
    }
