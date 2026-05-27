"""对话对象推断引擎 — 从对话上下文推断addressee"""
import sys, json, re
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

INPUT = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_annotated.json'
OUTPUT = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_with_addressee.json'

MAIN_CHARS = ['凉宫春日', '阿虚', '长门有希', '朝比奈实玖瑠', '古泉一树']

# 角色名称识别表：{文本中出现的形态: 标准化角色名}
# 注意：key按匹配优先级排列
NAME_PATTERNS = [
    (r'(?<!阿)虚(?!木)', '阿虚'),          # "阿虚" 或单独的 "虚", 排除 "虚无" "虚实"等
    (r'团长(?!大人)', '凉宫春日'),           # "团长" = 春日(在SOS团语境)
    (r'(?<![伊东杂])凉宫春日', '凉宫春日'),  # 全名
    (r'(?<![穿和服的])春日(?!的和服)', '凉宫春日'), # "春日"
    (r'古泉同学|古泉君', '古泉一树'),
    (r'古泉(?!同学)', '古泉一树'),
    (r'(?<![穿和服的长])长门|有希|长门同学', '长门有希'),
    (r'实玖瑠|朝比奈|朝比奈同学', '朝比奈实玖瑠'),
]

# "学姐" 在SOS团语境下永远指朝比奈（她是唯一的学姐）
SENPAI_PATTERN = re.compile(r'学姐|学姐')

# 群体称呼
GROUP_PATTERNS = [re.compile(p) for p in [r'大家', r'你们', r'各位', r'全员', r'在座的各位']]

# 自言自语标记
SELF_TALK_PATTERNS = [re.compile(p) for p in [
    r'^……',      # 省略号开头
    r'……$',      # 省略号结尾
    r'^(哼|唉|啧|切)',  # 孤立叹词
]]

def load_data():
    with open(INPUT, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_question(text):
    """是否问句"""
    return '?' in text or '？' in text

def detect_direct_address(dialogue):
    """H1: 从文本中检测直接称呼"""
    speaker = dialogue['speaker']
    text = dialogue['text']

    found = []
    for pattern, char_name in NAME_PATTERNS:
        m = re.search(pattern, text)
        if m:
            # 排除自指：如果匹配到的名字就是说话者自己
            if char_name == speaker:
                continue
            found.append((m.start(), char_name))

    if not found:
        # 尝试检测"学姐"——在SOS团语境永远指朝比奈
        if SENPAI_PATTERN.search(text) and speaker != '朝比奈实玖瑠':
            return '朝比奈实玖瑠', 'direct_address_senpai'
        return None, None

    # 按出现位置排序，取最靠前的（通常最先叫谁就是对谁说）
    found.sort(key=lambda x: x[0])
    return found[0][1], 'direct_address'

def detect_group_address(dialogue):
    """H4: 群体称呼"""
    text = dialogue['text']
    for p in GROUP_PATTERNS:
        if p.search(text):
            return '全体', 'group_address'
    return None, None

def detect_self_talk(dialogue):
    """H5: 自言自语"""
    text = dialogue['text']
    for p in SELF_TALK_PATTERNS:
        if p.search(text):
            return '自言自语', 'self_talk'
    return None, None

def infer_all(dialogues):
    """主推理流程"""
    results = []

    # 先统计每个角色的对话对象分布（用于H6回退）
    char_addressee_counts = defaultdict(Counter)
    temp_results = []

    # 第一遍：H1 + H4 + H5（不依赖上下文的规则）
    for i, d in enumerate(dialogues):
        entry = dict(d)

        addressee, method = detect_direct_address(d)
        if addressee:
            entry['addressee'] = addressee
            entry['inference_method'] = method
            entry['inference_confidence'] = 'high'
            temp_results.append(entry)
            continue

        addressee, method = detect_group_address(d)
        if addressee:
            entry['addressee'] = addressee
            entry['inference_method'] = method
            entry['inference_confidence'] = 'low'
            temp_results.append(entry)
            continue

        addressee, method = detect_self_talk(d)
        if addressee:
            entry['addressee'] = addressee
            entry['inference_method'] = method
            entry['inference_confidence'] = 'low'
            temp_results.append(entry)
            continue

        # 暂空，第二遍填充
        temp_results.append(entry)

    # 第二遍：H2+H3（上下文依赖）和H6（回退）
    for i, entry in enumerate(temp_results):
        if 'addressee' in entry and entry['addressee']:
            # 已经通过H1/H4/H5解决
            char_addressee_counts[entry['speaker']][entry['addressee']] += 1
            results.append(entry)
            continue

        prev = dialogues[i-1] if i > 0 else None
        speaker = entry['speaker']

        # H2: 问句-回答
        if prev and is_question(prev['text']) and prev['speaker'] != speaker:
            entry['addressee'] = prev['speaker']
            entry['inference_method'] = 'qa_pair'
            entry['inference_confidence'] = 'medium'
        # H3: 对话邻接（上条是不同说话者→回复）
        elif prev and prev['speaker'] != speaker:
            entry['addressee'] = prev['speaker']
            entry['inference_method'] = 'adjacency'
            entry['inference_confidence'] = 'medium'
        # H6: 回退到最常对话对象
        else:
            # 如果该角色有已知偏好
            if char_addressee_counts[speaker]:
                most_common = char_addressee_counts[speaker].most_common(1)[0][0]
                entry['addressee'] = most_common
                entry['inference_method'] = 'fallback_relationship'
                entry['inference_confidence'] = 'low'
            else:
                entry['addressee'] = '未知'
                entry['inference_method'] = 'unknown'
                entry['inference_confidence'] = 'unknown'

        char_addressee_counts[speaker][entry['addressee']] += 1
        results.append(entry)

    return results

def evaluate(results):
    """输出推理评估报告，返回char_dist"""
    total = len(results)
    confidences = Counter(r['inference_confidence'] for r in results)
    methods = Counter(r['inference_method'] for r in results)

    print(f"推理报告:")
    print(f"  总对话数: {total}")
    print(f"  置信度分布:")
    for conf, n in confidences.most_common():
        print(f"    {conf}: {n} ({n/total*100:.1f}%)")
    print(f"  推理方法分布:")
    for method, n in methods.most_common():
        print(f"    {method}: {n} ({n/total*100:.1f}%)")

    # 各角色addressee分布
    char_dist = defaultdict(Counter)
    for r in results:
        if r['speaker'] in MAIN_CHARS:
            char_dist[r['speaker']][r['addressee']] += 1

    print(f"\n各角色对话对象分布:")
    for char in MAIN_CHARS:
        total_c = sum(char_dist[char].values())
        print(f"\n  {char} (共{total_c}条):")
        for addr, n in char_dist[char].most_common():
            pct = n/total_c*100 if total_c > 0 else 0
            print(f"    → {addr}: {n} ({pct:.1f}%)")

    return char_dist

def print_matrix(char_dist):
    """角色间对话量矩阵"""
    print(f"\n\n=== 角色间对话量矩阵 ===")
    header = f"{'说话者→对话对象':<16}"
    for c in MAIN_CHARS:
        header += f"{c:<12}"
    print(header)
    print("=" * 76)

    for s in MAIN_CHARS:
        total_s = sum(char_dist[s].values())
        row = f"{s:<16}"
        for a in MAIN_CHARS:
            n = char_dist[s].get(a, 0)
            pct = n/total_s*100 if total_s > 0 else 0
            row += f"{n}/{pct:.0f}%{'':<6}"
        print(row)

def main():
    dialogues = load_data()
    print(f"加载 {len(dialogues)} 条对话")

    results = infer_all(dialogues)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已保存: {OUTPUT}")

    char_dist = evaluate(results)
    print_matrix(char_dist)

if __name__ == '__main__':
    main()
