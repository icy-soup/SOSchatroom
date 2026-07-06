"""Load response engine config and character persona files."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "backend" / "config" / "chatroom.json"
PERSONA_DIR = PROJECT_ROOT / "backend" / "personas"

CHARACTER_NAMES = ["凉宫春日", "阿虚", "长门有希", "朝比奈实玖瑠", "古泉一树"]
CHARACTER_DIR_MAP = {
    "凉宫春日": "haruhi",
    "阿虚": "kyon",
    "长门有希": "nagato",
    "朝比奈实玖瑠": "mikuru",
    "古泉一树": "koizumi",
}


def load_persona(name: str) -> str:
    """Load a character's 200-word persona core."""
    dir_name = CHARACTER_DIR_MAP.get(name)
    if not dir_name:
        return ""
    path = PERSONA_DIR / f"{dir_name}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()


def get_character_api_config(name: str) -> dict:
    api_config = CONFIG.get("character_api_config", {})
    overrides = api_config.get(name, {})
    if not overrides:
        return {}
    return {
        "api_url": overrides.get("api_url"),
        "model": overrides.get("model"),
    }
