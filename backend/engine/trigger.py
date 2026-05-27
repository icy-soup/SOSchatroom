"""Trigger Layer — decide which character(s) should respond.

Uses real novel dialogue statistics from novel_probability_result.json.
Each character rolls independently (real chatroom behavior).
"""

import json
import random
from pathlib import Path

from config import CHARACTER_NAMES

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NOVEL_PROB_PATH = _PROJECT_ROOT / "data" / "analysis" / "novel_probability_result.json"

_novel_matrix: dict | None = None


def _load_novel_matrix() -> dict:
    global _novel_matrix
    if _novel_matrix is not None:
        return _novel_matrix
    try:
        with open(_NOVEL_PROB_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _novel_matrix = data.get("conditional_probability_matrix", {})
    except Exception as e:
        print(f"[trigger] Failed to load novel data: {e}")
        _novel_matrix = {}
    return _novel_matrix


def get_character_probs(last_speaker: str | None) -> dict[str, float]:
    """Get independent response probabilities from novel dialogue data."""
    matrix = _load_novel_matrix()

    if last_speaker and last_speaker in matrix:
        raw = matrix[last_speaker]
        if isinstance(raw, dict):
            probs = {k: v for k, v in raw.items()
                     if k in CHARACTER_NAMES and isinstance(v, (int, float))}
            if probs:
                return probs

    # Fallback: equal probability
    eq = 1.0 / len(CHARACTER_NAMES)
    return {c: eq for c in CHARACTER_NAMES}


def contains_direct_question(text: str) -> bool:
    q_marks = {"？", "?", "吗", "呢", "吧", "么"}
    return any(c in text for c in q_marks)


def check_at_mention(text: str) -> list[str]:
    mentioned = []
    for name, partials in _NAME_ALIASES.items():
        for alias in partials:
            if f"@{alias}" in text:
                mentioned.append(name)
                break
    return mentioned


def match_topic(text: str) -> list[str]:
    hits = []
    for char in CHARACTER_NAMES:
        for kw in _TOPIC_MAP.get(char, []):
            if kw in text:
                hits.append(char)
                break
    return hits


_TOPIC_MAP = {
    "凉宫春日": ["外星人", "未来人", "超能力者", "SOS团", "有趣", "无聊",
                 "新活动", "暑假", "学园祭", "UFO", "神秘", "决定了", "给我"],
    "阿虚": ["吐槽", "麻烦", "正常", "日常", "普通人", "叹气", "无奈",
             "妹妹", "谷口", "国木田", "烦", "累", "唉"],
    "长门有希": ["书", "阅读", "图书馆", "资讯", "数据", "分析", "调查",
                 "安静", "宇宙", "沉默"],
    "朝比奈实玖瑠": ["点心", "茶水", "女仆", "可爱", "害怕", "怎么办",
                     "时间", "未来", "抱歉", "对不起"],
    "古泉一树": ["机关", "闭锁空间", "神人", "超能力", "棋盘", "策略",
                 "推测", "理论", "人类原理", "开玩笑"],
}


_NAME_ALIASES = {
    "凉宫春日": ["凉宫春日", "凉宫", "春日", "团长"],
    "阿虚": ["阿虚", "虚", "キョン"],
    "长门有希": ["长门有希", "长门", "有希", "Yuki"],
    "朝比奈实玖瑠": ["朝比奈实玖瑠", "朝比奈", "实玖瑠", "实玖瑠"],
    "古泉一树": ["古泉一树", "古泉", "一树", "Itsuki"],
}


def get_last_bot_speaker(conversation_history: list[dict]) -> str | None:
    """从对话历史找到最后一个 bot 发言的角色。"""
    for entry in reversed(conversation_history):
        if entry.get("is_bot"):
            return entry["character"]
    return None


def select_responders(
    last_speaker: str | None,
    message_text: str,
    user_character: str,
    existing_responders: set[str],
    conversation_history: list[dict] | None = None,
    absent: list[str] | None = None,
) -> list[str]:
    """
    结合语境和概率选择回复角色。

    决策顺序：
    1. @提及 → 强制回复
    2. 含角色名的直接提问 → 被问者回复
    3. 独立概率 roll（含语境补正：上一位对话对象高概率、话题匹配）
    """
    # 1. @mention -> 100%强制回复
    at_mentioned = check_at_mention(message_text)
    if at_mentioned:
        at_mentioned = [c for c in at_mentioned if c != user_character]
        if absent:
            at_mentioned = [c for c in at_mentioned if c not in absent]
        if at_mentioned:
            return at_mentioned

    # 2. 直接提问中含角色名 -> 被问的人回复
    named_target = None
    if contains_direct_question(message_text):
        for name, partials in _NAME_ALIASES.items():
            if name == user_character:
                continue
            for alias in partials:
                if alias in message_text:
                    named_target = name
                    break
            if named_target:
                break

    if named_target:
        if not absent or named_target not in absent:
            return [named_target]

    # 3. 独立概率 roll（含语境补正）
    raw = get_character_probs(last_speaker)
    last_bot = None
    if conversation_history:
        last_bot = get_last_bot_speaker(conversation_history)

    candidates = []

    for char, prob in raw.items():
        if char == user_character or char in existing_responders:
            continue

        # 小说概率是轮流制，聊天室需要独立决策
        # 每个非用户角色至少30%的接话概率，确保对话多样性
        adjusted = max(prob * 2.0, 0.30)

        # 低概率角色（原作对话少）额外补正，保证参与感
        if prob < 0.10:
            adjusted += 0.10

        # 话题匹配再追加
        if char in match_topic(message_text):
            adjusted += 0.30

        # 语境连贯：说"你"时，上一位对话对象高概率接话（但不独占）
        if "你" in message_text and last_bot and char == last_bot:
            adjusted += 0.80

        candidates.append((char, prob, adjusted))

    # Filter absent characters
    if absent:
        candidates = [(c, p, a) for c, p, a in candidates if c not in absent]

    # Roll
    selected = [(char, prob) for char, prob, adj in candidates if random.random() < adj]

    # 按原始概率降序排列（概率高的先回复）
    selected.sort(key=lambda x: x[1], reverse=True)

    # 兜底：无人被选中时，返回概率最高的角色
    if not selected and candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = [(candidates[0][0], candidates[0][1])]

    # Filter absent characters from final selection
    if absent:
        selected = [(c, p) for c, p in selected if c not in absent]

    # If all absent characters removed, fallback to first non-absent
    if not selected and absent:
        for c in CHARACTER_NAMES:
            if c != user_character and c not in absent and c not in existing_responders:
                return [c]

    return [c for c, _ in selected]
