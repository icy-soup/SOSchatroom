"""从图谱 + episodes 原文生成角色人设 + 知识边界。
用法:  python generate_persona.py [--numbered]
       --numbered: 重名时生成带序号的副本（xxx_1.txt, xxx_2.txt...）"""
import sys, os, re, argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend"))

from graphrag.store import GraphStore
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"), override=True)

# 5 个主要角色
CHARACTERS = {
    "凉宫春日": "haruhi",
    "阿虚": "kyon",
    "长门有希": "nagato",
    "朝比奈实玖瑠": "mikuru",
    "古泉一树": "koizumi",
}

PERSONA_DIR = os.path.join(_PROJECT_ROOT, "backend", "personas")

# ── Prompt：人设生成（三源合并）────────────────────────────────

PERSONA_PROMPT = """你是一个凉宫春日系列小说的角色分析专家。
根据给定的图谱数据和原文片段，为该角色撰写一段 600-1000 字的角色人设。
这段人设将用于 AI 角色扮演对话的 System Prompt。

你将获得三部分信息：
1. 【图谱关系】—— 该角色与其他实体的关联（含简短事实描述）
2. 【原文片段】—— 该角色在小说中出现的实际段落
3. 【角色摘要】—— 图谱对该角色的概括

请基于以上信息，撰写人设，要求：
1. 用第二人称「你」开头（「你是XXX——」）
2. 必须包含：
   - 身份背景
   - 性格特征
   - 说话风格和常用语气
   - 关键人际关系（谁对你重要、关系如何）
   - 典型行为模式
3. 外貌描写必须严格从【原文片段】中提取，不得自己编造
4. 语气生动，符合角色给人的印象
5. 600-1000 字
6. 不要使用列表符号，写成连贯的段落
7. 必须基于给定的数据，不要编造不存在的关系或事件"""

# ── Prompt：知识边界 ──────────────────────────────────────────

# ── Prompt：台词提取 ──────────────────────────────────────────

QUOTE_PROMPT = """你是一个凉宫春日系列小说的台词分析师。
从给定的原文片段中，提取该角色最有代表性的 5-8 句原话（台词）。
这些原话将用于 AI 角色扮演对话的说话风格参考。

要求：
1. 只提取该角色亲口说的原话，不要总结或转述
2. 选择最能体现角色性格和说话风格的句子
3. 包含不同的语气：命令、吐槽、疑问、感叹等
4. 每句原话用「」包起来
5. 直接输出，不要额外说明

输出格式：
[说话风格参考]
以下是你过去说过的原话——请模仿这种语气和用词：
- 「原话1」
- 「原话2」
- ……"""

BOUNDARY_PROMPT = """你是一个凉宫春日系列小说的设定专家。
根据给定的角色信息和原文片段，列出该角色「绝对不知道的事」——这些是该角色在故事中不可能知道的信息。

注意区分不同角色：
- 凉宫春日：不知道团里有外星人/未来人/超能力者，不知道闭锁空间，不知道自己的真正能力
- 阿虚：知道所有真相，但他的任务是「不让春日知道」
- 长门有希：几乎知道所有事
- 朝比奈实玖瑠：知道未来的事情但「禁止事项」不能说
- 古泉一树：知道机关和超能力的真相

输出格式（直接输出，不要额外内容）：
[知识边界]
以下是你不知道的事——绝对不能在对话中提及：
- 你不知道……
- 你不知道……
- 你不知道……"""


# ── 工具函数 ──────────────────────────────────────────────────


def build_entity_context(store, name):
    """从图谱读取实体的所有关联信息（排除隐藏节点）。"""
    node = store.get_node_by_name(name)
    if not node:
        return None, None

    settings = store.get_settings()
    hidden_nodes = set(settings.get("hidden_nodes", []))
    edges = store.get_edges_for_node(node["uuid"])
    all_nodes = {n["uuid"]: n for n in store.get_all_nodes()}

    visible_edges = []
    for e in edges:
        other = e["source_node_uuid"] if e["target_node_uuid"] == node["uuid"] else e["target_node_uuid"]
        if other in hidden_nodes:
            continue
        visible_edges.append(e)

    lines = [f"实体: {name}", f"摘要: {node.get('summary', '')}", ""]
    for e in visible_edges:
        src = all_nodes.get(e["source_node_uuid"], {}).get("name", "?")
        tgt = all_nodes.get(e["target_node_uuid"], {}).get("name", "?")
        rel = e.get("name", "")
        fact = e.get("fact", "")
        if fact:
            lines.append(f"  {src} —[{rel}]→ {tgt}: {fact}")
        else:
            lines.append(f"  {src} —[{rel}]→ {tgt}")

    return "\n".join(lines), node


def build_episode_context(store, name, max_episodes=5):
    """从 episodes 中搜索该角色相关的原文段落。"""
    results = store.search_episodes(name, limit=max_episodes)
    if not results:
        return "（未找到相关原文片段）"

    parts = []
    for r in results:
        data = r.get("data", "")
        # 截取含角色名的附近段落
        idx = data.find(name)
        if idx < 0:
            continue
        start = max(0, idx - 200)
        end = min(len(data), idx + len(name) + 400)
        snippet = data[start:end].strip()
        # 截到句子边界
        if start > 0:
            prev = snippet.find("。")
            if prev > 0 and prev < len(snippet) // 2:
                snippet = snippet[prev + 1:].strip()
        if end < len(data):
            last = max(snippet.rfind("。"), snippet.rfind("\n"))
            if last > len(snippet) // 2:
                snippet = snippet[:last + 1]
        parts.append(snippet)
        if len(parts) >= max_episodes:
            break

    return "\n---\n".join(parts)


def call_llm(client, model, system, user):
    """调 LLM，带重试。"""
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.5,
                max_tokens=2048,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 2:
                print(f"  重试 {attempt+2}/3: {e}")
                import time
                time.sleep(1)
            else:
                print(f"  LLM 调用失败: {e}")
                return ""


def next_filename(dir_path, base_name):
    """Windows 风格重名处理：存在 xxx.txt 则返回 xxx_1.txt，以此类推。"""
    path = os.path.join(dir_path, f"{base_name}.txt")
    if not os.path.exists(path):
        return path
    n = 1
    while True:
        path = os.path.join(dir_path, f"{base_name}_{n}.txt")
        if not os.path.exists(path):
            return path
        n += 1


# ── 主流程 ──────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numbered", action="store_true", help="重名时生成带序号的副本")
    args = parser.parse_args()

    # 清理 ANSI 码
    _ansi_clean = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    for _key in ("ANTHROPIC_API_KEY", "ANTHROPIC_API_URL", "ANTHROPIC_MODEL"):
        _val = os.environ.get(_key, "")
        if _val:
            os.environ[_key] = _ansi_clean.sub("", _val)

    from openai import OpenAI
    import httpx

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_url = os.environ.get("ANTHROPIC_API_URL", "https://api.deepseek.com")
    model = os.environ.get("ANTHROPIC_MODEL", "deepseek-chat")

    if not api_key:
        print("错误: ANTHROPIC_API_KEY 未配置")
        return

    client = OpenAI(api_key=api_key, base_url=api_url, http_client=httpx.Client(timeout=300.0))
    store = GraphStore("haruhi_novel")
    os.makedirs(PERSONA_DIR, exist_ok=True)

    for name, dir_name in CHARACTERS.items():
        print(f"\n{'=' * 40}")
        print(f"生成: {name}")
        print(f"{'=' * 40}")

        # 1. 图谱数据
        graph_ctx, node = build_entity_context(store, name)
        if not node:
            print(f"  ⚠ 图谱中未找到「{name}」，跳过")
            continue
        edge_count = graph_ctx.count("—[")
        print(f"  [图] {edge_count} 条关联边")

        # 2. episodes 原文
        ep_ctx = build_episode_context(store, name, max_episodes=4)
        ep_count = ep_ctx.count("---") + 1 if "---" in ep_ctx else (1 if ep_ctx and "未找到" not in ep_ctx else 0)
        print(f"  [原文] {ep_count} 段相关片段")

        # 3. 人设生成（图 + 原文合并）
        user_msg = (
            f"请为角色「{name}」撰写角色人设。\n\n"
            f"===== 【图谱关系】 =====\n{graph_ctx}\n\n"
            f"===== 【原文片段】 =====\n{ep_ctx}"
        )
        persona = call_llm(client, model, PERSONA_PROMPT, user_msg)
        if not persona:
            print(f"  ⚠ 人设生成失败，跳过")
            continue

        # 3b. 原话台词提取（从 episodes 提取角色经典原话）
        quotes = ""
        if ep_ctx and "未找到" not in ep_ctx:
            quote_input = f"角色名称：{name}\n\n原文片段：\n{ep_ctx[:3000]}"
            quotes = call_llm(client, model, QUOTE_PROMPT, quote_input)
            if quotes:
                print(f"  [台词] 已提取角色原话")

        # 4. 知识边界
        boundary_user = (
            f"角色名称：{name}\n\n"
            f"===== 【角色图谱关系】 =====\n{graph_ctx[:2000]}\n\n"
            f"===== 【角色原文片段】 =====\n{ep_ctx[:2000]}"
        )
        boundary = call_llm(client, model, BOUNDARY_PROMPT, boundary_user)
        if boundary and "知识边界" not in boundary:
            boundary = "[知识边界]\n以下是你不知道的事——绝对不能在对话中提及：\n" + boundary

        # 5. 合并输出：人设 + 原话 + 知识边界
        full_output = persona
        if quotes:
            full_output += "\n\n" + quotes
        if boundary:
            full_output += "\n\n" + boundary

        if args.numbered:
            out_path = next_filename(PERSONA_DIR, dir_name)
        else:
            out_path = os.path.join(PERSONA_DIR, f"{dir_name}.txt")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_output)

        print(f"  ✓ 已写入 {os.path.basename(out_path)} ({len(full_output)} 字)")
        print(f"  --- 人设开头 ---\n{persona[:150]}...\n  ---")

    print(f"\n完成！文件在: {PERSONA_DIR}")


if __name__ == "__main__":
    main()
