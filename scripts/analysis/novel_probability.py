"""
从凉宫春日小说全13卷提取对话 → 计算响应概率矩阵
"""
import sys, re, json, os
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# ===== 角色名称映射（含各种称呼变体）=====
CHARACTER_NAMES = {
    '凉宫春日': ['凉宫春日', '春日', '凉宫'],
    '阿虚': ['阿虚', '虚'],
    '长门有希': ['长门有希', '长门', '有希'],
    '朝比奈实玖瑠': ['朝比奈实玖瑠', '朝比奈', '实玖瑠', '实久留', '实玖留'],
    '古泉一树': ['古泉一树', '古泉', '一树'],
    '鹤屋': ['鹤屋', '鹤屋学姐', '鹤屋同学'],
}

# 所有称呼变体 → 标准角色名
NAME_MAP = {}
for standard, variants in CHARACTER_NAMES.items():
    for v in variants:
        NAME_MAP[v] = standard

# 说话动词模式
SPEAK_VERBS = ['说', '道', '曰', '问', '答', '叫', '喊', '骂', '回答', '开口', '回应', '喃喃自语', '哼', '大叫', '低声', '插嘴', '附和']

def load_volumes(base_dir):
    """加载全部13卷文本"""
    texts = []
    # 卷1-11
    path = os.path.join(base_dir, '1-11凉宫春日物语.txt')
    with open(path, 'r', encoding='utf-8') as f:
        texts.append(('1-11', f.read()))

    # 卷12-13
    for vol in ['12', '13']:
        path = os.path.join(base_dir, f'{vol}凉宫春日物语.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                texts.append((vol, f.read()))

    return texts

def extract_dialogues_with_context(text):
    """
    从文本中提取所有「...」对话及其前文
    返回: [(dialogue_text, prev_context, position)]
    """
    dialogues = []
    # 按「分割
    parts = text.split('「')
    pos = 0
    for i in range(1, len(parts)):
        if '」' in parts[i]:
            dia, rest = parts[i].split('」', 1)
            # 前文: 前一个split段的末尾
            prev = parts[i-1][-200:] if len(parts[i-1]) > 200 else parts[i-1]
            prev = prev.replace('\n', ' ').strip()
            dialogues.append((dia.strip(), prev, pos + len(parts[i-1])))
        pos += len(parts[i-1]) + 1
    return dialogues

def identify_speaker(dialogue, prev_context):
    """
    根据对话和前文识别说话者。
    返回: (speaker_name, confidence: 'high'/'medium'/'low')
    """
    # 策略1: 前文结尾有「XX说」模式
    # 如: 「对话」XX说 或 XX说：「对话」或 XX道：「对话」
    for name_std, name_variants in CHARACTER_NAMES.items():
        for v in name_variants:
            # 模式: XX说「对话」(前文以XX说结尾)
            for verb in SPEAK_VERBS:
                pattern1 = f'{v}{verb}'
                if prev_context.endswith(pattern1):
                    return name_std, 'high'
                # 模式: 「对话」XX说（对话后接XX说 — 需要看前文开头）
                # 但这种情况prev_context是「之前的文本，所以检查prev_context是否以XX说开头不适用
                # 实际上这种情况的prev_context可能是空的或者有其他内容

            # 模式: XX在前文中出现且靠近结尾
            if v in prev_context[-60:]:
                # 检查是否是"XX说"的变体
                idx = prev_context.rfind(v)
                if idx >= 0:
                    after = prev_context[idx+len(v):idx+len(v)+1]
                    if after in ['说', '道', '曰', '问', '答', '叫', '喊', '骂']:
                        return name_std, 'high'

    # 策略2: 前文包含明确XX说但不以它结尾（可能中间有修饰语）
    for name_std, name_variants in CHARACTER_NAMES.items():
        for v in name_variants:
            for verb in SPEAK_VERBS:
                if f'{v}{verb}' in prev_context[-80:]:
                    return name_std, 'high'

    # 策略3: 对话内容本身暗示说话者（如包含其他人的名字）
    for name_std, name_variants in CHARACTER_NAMES.items():
        for v in name_variants:
            if v in dialogue and name_std != '阿虚':
                # 如果对话提到某人名字，可能不是那个人在说话
                # 但这不是可靠指标
                pass

    return None, 'low'

def compute_transition_matrix(all_dialogues):
    """
    从带speaker标注的对话列表计算转移矩阵。
    """
    # 只保留有speaker的对话
    valid = [d for d in all_dialogues if d['speaker']]

    # 统计每个角色说了多少次
    speak_counts = Counter(d['speaker'] for d in valid)
    characters = sorted(speak_counts.keys())

    # 统计转移次数 (A说→B说)
    transitions = Counter()
    for i in range(len(valid) - 1):
        curr = valid[i]['speaker']
        nxt = valid[i+1]['speaker']
        if curr != nxt:
            transitions[(curr, nxt)] += 1

    # 构建条件概率矩阵 P(回应者|说话者)
    matrix = {}
    for speaker in characters:
        total = speak_counts[speaker]
        matrix[speaker] = {}
        for responder in characters:
            if speaker == responder:
                matrix[speaker][responder] = 0
            else:
                matrix[speaker][responder] = transitions.get((speaker, responder), 0) / total if total > 0 else 0

    return matrix, speak_counts, characters, valid

def extract_narrative_dialogues(text):
    """
    更精确的方法: 逐段分析文本，跟踪叙事场景中的"当前活跃角色"
    """
    import re

    paragraphs = text.split('\n\n')
    dialogues = []
    current_scene_chars = set()
    last_attributed_speaker = None

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 检测段落中出现的角色名（谁在这个场景里）
        scene_chars = set()
        for name_std, variants in CHARACTER_NAMES.items():
            for v in variants:
                if v in para:
                    scene_chars.add(name_std)
        if scene_chars:
            current_scene_chars = scene_chars

        # 找这个段落里的所有「」
        parts = para.split('「')
        for i in range(1, len(parts)):
            if '」' in parts[i]:
                dia, after = parts[i].split('」', 1)
                dia = dia.strip()
                if len(dia) < 1:
                    # 空对话（如「……」）保留
                    pass

                # 前文 = 前一个split段落后50字
                prev = parts[i-1][-80:] if len(parts[i-1]) > 80 else parts[i-1]
                prev = prev.replace('\n', '').strip()

                # 后文 = dialogue后30字
                after = after[:30].replace('\n', '').strip()

                speaker = None
                confidence = 'low'

                # --- 试识别说话者 ---
                # 1. 前文以 "XX说" 结尾
                if not speaker:
                    for name_std, variants in CHARACTER_NAMES.items():
                        for v in variants:
                            for verb in SPEAK_VERBS:
                                pat = f'{v}{verb}'
                                if prev.endswith(pat):
                                    speaker = name_std
                                    confidence = 'high'
                                    break
                            if speaker: break
                        if speaker: break

                # 2. 后文以 "XX说" 开头（「对话」XX说）
                if not speaker:
                    for name_std, variants in CHARACTER_NAMES.items():
                        for v in variants:
                            for verb in SPEAK_VERBS:
                                pat = f'{v}{verb}'
                                if after.startswith(pat):
                                    speaker = name_std
                                    confidence = 'high'
                                    break
                            if speaker: break
                        if speaker: break

                # 3. 前文的最后一句是 "XX说" 形式
                if not speaker:
                    for name_std, variants in CHARACTER_NAMES.items():
                        for v in variants:
                            for verb in SPEAK_VERBS:
                                pat = f'{v}{verb}'
                                idx = prev.rfind(pat)
                                if idx >= 0 and idx > len(prev) - 40:
                                    speaker = name_std
                                    confidence = 'high'
                                    break
                            if speaker: break
                        if speaker: break

                # 4. 前文包含明确的 XX问/叫/喊
                if not speaker:
                    for name_std, variants in CHARACTER_NAMES.items():
                        for v in variants:
                            for verb in ['说', '道', '问', '答', '叫', '喊', '开口', '回应']:
                                pat = f'{v}{verb}'
                                if pat in prev[-60:]:
                                    speaker = name_std
                                    confidence = 'medium'
                                    break
                            if speaker: break
                        if speaker: break

                # 5. 如果对话包含对某人的称呼
                if not speaker:
                    for name_std, variants in CHARACTER_NAMES.items():
                        for v in variants:
                            for other_std, other_variants in CHARACTER_NAMES.items():
                                if other_std != name_std:
                                    for ov in other_variants:
                                        if ov in dia[:30] and v not in dia[:10]:
                                            # 说话者不太可能是被称呼的人
                                            # 但也不一定
                                            pass

                # 6. 使用最后已知说话者
                if not speaker:
                    speaker = last_attributed_speaker
                    confidence = 'low'

                # 7. 如果场景中只有一个角色+阿虚，而说话者还没确定
                if not speaker:
                    # 大部分情况下是阿虚在叙述，但这里保守一点
                    pass

                if speaker:
                    dialogues.append({
                        'speaker': speaker,
                        'text': dia,
                        'confidence': confidence,
                        'scene_chars': list(current_scene_chars),
                    })
                    if confidence in ('high', 'medium'):
                        last_attributed_speaker = speaker

    return dialogues

def print_statistics(speak_counts, matrix, characters, total_dialogues):
    """打印统计结果"""
    print(f"\n{'='*60}")
    print(f"对话总数: {total_dialogues}")
    print(f"{'='*60}")

    print(f"\n【各角色对话量】")
    print(f"{'角色':<12} {'次数':>6} {'占比':>8}")
    print(f"{'-'*30}")
    total = sum(speak_counts.values())
    for name, count in sorted(speak_counts.items(), key=lambda x: -x[1]):
        print(f"{name:<12} {count:>6} {count/total*100:>7.1f}%")

    print(f"\n【条件概率矩阵 P(回应|触发)】")
    # 表头
    header = f"{'触发\\回应':<12}"
    for c in characters:
        header += f"{c:<12}"
    print(header)

    for speaker in characters:
        row = f"{speaker:<12}"
        for responder in characters:
            prob = matrix[speaker].get(responder, 0) * 100
            if prob > 0:
                row += f"{prob:>5.1f}%    "
            else:
                row += f"{'—':<12}"
        print(row)

    print(f"\n【Top 回应链】")
    transitions = []
    for s in characters:
        for r in characters:
            if s != r and matrix[s].get(r, 0) > 0:
                transitions.append((s, r, matrix[s][r]))
    transitions.sort(key=lambda x: -x[2])
    for s, r, p in transitions[:10]:
        print(f"  {s} → {r}: {p*100:.1f}%")

# ===== 主流程 =====
base_dir = r'F:\Extra Learning\github\haruhi-skill\reference'

print("加载文本...")
volumes = load_volumes(base_dir)
full_text = vols_text = '\n'.join([t for _, t in volumes])
print(f"总字符数: {len(full_text)}")

print("\n提取对话...")
dialogues = extract_narrative_dialogues(full_text)
print(f"提取到 {len(dialogues)} 条对话")

# 按置信度统计
high_conf = sum(1 for d in dialogues if d['confidence'] == 'high')
med_conf = sum(1 for d in dialogues if d['confidence'] == 'medium')
low_conf = sum(1 for d in dialogues if d['confidence'] == 'low')
print(f"  高置信度: {high_conf} | 中: {med_conf} | 低: {low_conf}")

# 计算矩阵
matrix, speak_counts, characters, valid = compute_transition_matrix(dialogues)
print_statistics(speak_counts, matrix, characters, len(dialogues))

# 保存结果
output = {
    'total_dialogues': len(dialogues),
    'high_confidence': high_conf,
    'medium_confidence': med_conf,
    'low_confidence': low_conf,
    'speak_counts': dict(speak_counts),
    'conditional_probability_matrix': {
        s: {r: round(matrix[s].get(r, 0)*100, 1) for r in characters}
        for s in characters
    },
    'characters': characters,
}

out_path = r'F:\Extra Learning\github\haruhi-skill\reference\novel_probability_result.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: {out_path}")

# 保存对话样本
out_dia = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_sample.txt'
with open(out_dia, 'w', encoding='utf-8') as f:
    for d in dialogues[:100]:
        f.write(f"[{d['speaker']}]({d['confidence']})「{d['text']}」\n")
print(f"对话样本: {out_dia}")
