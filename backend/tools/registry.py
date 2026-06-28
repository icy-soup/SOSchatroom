"""工具注册表 —— 扫描 haruhi-skill/tools/<id>/prompt.txt 动态加载。"""

from pathlib import Path
from typing import Optional

# 指向根目录 tools/（相对于 backend/tools/registry.py 的位置）
_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"

# 工具 → 角色映射
_TOOL_CHARACTER: dict[str, str] = {
    "action-engine": "凉宫春日",
    "vitality-radar": "凉宫春日",
    "anti-inspiration": "阿虚",
}


def load_tool_prompt(tool_id: str) -> Optional[str]:
    """读取工具 prompt 文件，若不存在返回 None。
    自动将工具 ID 中的下划线转为连字符以匹配目录名。"""
    dir_name = tool_id.replace("_", "-")
    prompt_file = _TOOLS_DIR / dir_name / "prompt.txt"
    if not prompt_file.exists():
        return None
    return prompt_file.read_text("utf-8").strip()


def get_character_for_tool(tool_id: str) -> Optional[str]:
    dir_name = tool_id.replace("_", "-")
    return _TOOL_CHARACTER.get(dir_name)


def get_tool_ids() -> list[str]:
    if not _TOOLS_DIR.exists():
        return []
    ids: list[str] = []
    for entry in _TOOLS_DIR.iterdir():
        if entry.is_dir() and (entry / "prompt.txt").exists():
            ids.append(entry.name)
    return ids
