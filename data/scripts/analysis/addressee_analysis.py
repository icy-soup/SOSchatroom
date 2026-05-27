"""对话对象分析与回应方式特征提取"""
import sys, json, re
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

INPUT = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_with_addressee.json'
OUTPUT_ANALYSIS = r'F:\Extra Learning\github\haruhi-skill\reference\addressee_analysis_result.json'
OUTPUT_MATRIX = r'F:\Extra Learning\github\haruhi-skill\reference\addressee_relationship_matrix.json'

MAIN_CHARS = ['凉宫春日', '阿虚', '长门有希', '朝比奈实玖瑠', '古泉一树']

# 语气词/句末词
PARTICLES = ['吧', '吗', '呢', '啊', '嘛', '哟', '啦', '哦', '嗯', '呀', '耶', '喔', '呗']

# 确定性标记
CERTAIN_HIGH = ['绝对', '当然', '一定', '肯定', '必定', '毫无疑问', '必须']
CERTAIN_LOW = ['可能', '大概', '也许', '或许', '应该', '说不定', '好像', '似乎']

# 礼貌表达
POLITE_MARKERS = ['请', '谢谢', '抱歉', '对不起', '不好意思', '麻烦', '劳驾']

# 感叹/命令标记
EXCLAMATION_PATTERN = re.compile(r'[！!]')
COMMAND_PATTERNS = [re.compile(p) for p in [
    r'^你给我', r'^给我', r'^你(给我|快去|赶快|快点)',
    r'^不许', r'^不准', r'^少废话', r'^闭嘴',
    r'(过来|过来一下|跟我来|拿去|收下)[！!。]?$',
]]

# 软化表达
SOFTENING = ['吧', '嘛', '呢', '好不好', '行不行', '可以吗']

# 亲密称呼
INTIMATE_TERMS = {
    '阿虚': True,
    '实玖瑠': True,
    '有希': True,
    '古泉': False,  # 古泉不叫亲密称呼
}


def load_data():
    with open(INPUT, 'r', encoding='utf-8') as f:
        return json.load(f)


def classify_tone(entry):
    """对单条对话做语气分类"""
    text = entry['text']
    features = {}

    # 句子长度
    features['char_count'] = len(text)

    # 问句
    features['is_question'] = 1 if ('?' in text or '？' in text) else 0

    # 感叹
    features['is_exclamation'] = 1 if EXCLAMATION_PATTERN.search(text) else 0

    # 命令
    features['is_command'] = 1 if any(p.search(text) for p in COMMAND_PATTERNS) else 0

    # 语气词统计
    particle_counts = {}
    for p in PARTICLES:
        c = text.count(p)
        if c > 0:
            particle_counts[p] = c
    features['particles'] = particle_counts

    # 确定性标记
    features['certain_high'] = sum(1 for m in CERTAIN_HIGH if m in text)
    features['certain_low'] = sum(1 for m in CERTAIN_LOW if m in text)

    # 礼貌表达
    features['politeness'] = sum(1 for m in POLITE_MARKERS if m in text)

    # 软化表达
    features['softening'] = sum(1 for m in SOFTENING if m in text)

    # 亲密称呼
    features['intimate_term'] = 1 if any(
        term in text for term in INTIMATE_TERMS
    ) else 0

    # 首2字符（句首特征）
    features['opener_2'] = text[:2] if len(text) >= 2 else text

    return features


def compute_baseline(speaker_entries):
    """计算角色自身的基准特征"""
    all_features = [classify_tone(e) for e in speaker_entries]
    n = len(all_features)
    if n == 0:
        return {}

    return {
        'total_dialogues': n,
        'avg_char_count': sum(f['char_count'] for f in all_features) / n,
        'question_ratio': sum(f['is_question'] for f in all_features) / n,
        'exclamation_ratio': sum(f['is_exclamation'] for f in all_features) / n,
        'command_ratio': sum(f['is_command'] for f in all_features) / n,
        'politeness_per_dialogue': sum(f['politeness'] for f in all_features) / n,
        'softening_per_dialogue': sum(f['softening'] for f in all_features) / n,
        'certain_high_ratio': sum(f['certain_high'] for f in all_features) / n,
        'certain_low_ratio': sum(f['certain_low'] for f in all_features) / n,
        'intimate_term_ratio': sum(f['intimate_term'] for f in all_features) / n,
    }


def compute_pair_stats(entries, baseline):
    """计算(speaker, addressee)对的语言特征"""
    all_features = [classify_tone(e) for e in entries]
    n = len(all_features)
    if n == 0:
        return None

    # 语气词合并分布
    combined_particles = Counter()
    for f in all_features:
        for p, c in f['particles'].items():
            combined_particles[p] += c

    # 句首词统计
    openers = Counter(f['opener_2'] for f in all_features)

    # 代表性对话（选择最典型的中长句）
    candidates = sorted(
        [(abs(f['char_count'] - baseline.get('avg_char_count', 15)), i, e)
         for i, (f, e) in enumerate(zip(all_features, entries))],
        key=lambda x: x[0]
    )
    representatives = [e['text'] for _, _, e in candidates[:5]]

    stats = {
        'dialogue_count': n,
        'avg_char_count': sum(f['char_count'] for f in all_features) / n,
        'question_ratio': sum(f['is_question'] for f in all_features) / n,
        'exclamation_ratio': sum(f['is_exclamation'] for f in all_features) / n,
        'command_ratio': sum(f['is_command'] for f in all_features) / n,
        'politeness_per_dialogue': sum(f['politeness'] for f in all_features) / n,
        'softening_per_dialogue': sum(f['softening'] for f in all_features) / n,
        'certain_high_ratio': sum(f['certain_high'] for f in all_features) / n,
        'certain_low_ratio': sum(f['certain_low'] for f in all_features) / n,
        'intimate_term_ratio': sum(f['intimate_term'] for f in all_features) / n,
        'top_particles': dict(combined_particles.most_common(5)),
        'top_openers': dict(openers.most_common(5)),
        'representative_dialogues': representatives,
    }

    # VS基准值的偏差
    if baseline:
        delta = {}
        for key in ['avg_char_count', 'question_ratio', 'exclamation_ratio',
                     'command_ratio', 'politeness_per_dialogue',
                     'softening_per_dialogue', 'intimate_term_ratio']:
            base_val = baseline.get(key, 0)
            if base_val:
                delta[key.replace('_ratio', '_delta').replace('_per_dialogue', '_delta')] = \
                    round(stats[key] - base_val, 3)
        stats['vs_baseline'] = delta

    return stats


def generate_relationship_label(stats, baseline):
    """根据特征生成关系类型标签"""
    if stats is None or not baseline:
        return "未知"

    tags = []
    d = stats.get('vs_baseline', {})

    cmd_delta = d.get('command_delta', 0)
    pol_delta = d.get('politeness_delta', 0)
    int_delta = d.get('intimate_term_delta', 0)
    exc_delta = d.get('exclamation_delta', 0)

    if cmd_delta > 0.05:
        tags.append("命令式")
    elif cmd_delta < -0.05:
        tags.append("礼貌式")

    if int_delta > 0.02:
        tags.append("亲近")
    elif int_delta < -0.02:
        tags.append("疏离")

    if exc_delta > 0.05:
        tags.append("热烈")
    elif exc_delta < -0.05:
        tags.append("冷静")

    if pol_delta > 0.05:
        tags.append("敬语")

    if not tags:
        tags.append("中性")

    return "/".join(tags)


def main():
    data = load_data()
    print(f"加载 {len(data)} 条对话")

    # 按(speaker, addressee)分组
    pairs = defaultdict(list)
    for d in data:
        pairs[(d['speaker'], d['addressee'])].append(d)

    # 计算每个角色的基准特征
    baseline_by_speaker = {}
    for char in MAIN_CHARS:
        char_entries = [d for d in data if d['speaker'] == char]
        baseline_by_speaker[char] = compute_baseline(char_entries)

    # 打印基准特征
    print(f"\n【各角色基准语言特征】")
    for char in MAIN_CHARS:
        b = baseline_by_speaker[char]
        if not b:
            continue
        print(f"\n{char}:")
        print(f"  平均句长: {b['avg_char_count']:.1f}字")
        print(f"  疑问比例: {b['question_ratio']*100:.0f}%")
        print(f"  感叹比例: {b['exclamation_ratio']*100:.0f}%")
        print(f"  命令比例: {b['command_ratio']*100:.0f}%")
        print(f"  礼貌比例: {b['politeness_per_dialogue']*100:.0f}%")
        print(f"  亲密称呼比例: {b['intimate_term_ratio']*100:.0f}%")

    # 计算每对特征
    print(f"\n【角色间回应方式分析】")
    analysis = {}
    for (speaker, addressee), entries in pairs.items():
        if speaker not in MAIN_CHARS:
            continue
        if addressee not in MAIN_CHARS and addressee not in ['全体', '自言自语']:
            # 也分析非主要角色但主要角色对其说话的情况
            pass

        stats = compute_pair_stats(entries, baseline_by_speaker.get(speaker))
        if stats is None:
            continue

        label = generate_relationship_label(stats, baseline_by_speaker.get(speaker))

        pair_key = f"{speaker}→{addressee}"
        analysis[pair_key] = stats
        analysis[pair_key]['relationship_label'] = label

        # 打印摘要（仅主要addressee）
        if addressee in MAIN_CHARS:
            d = stats.get('vs_baseline', {})
            delta_str = ", ".join(
                f"{k.replace('_delta','')}{v:+.0%}" for k, v in d.items()
                if abs(v) > 0.02
            ) if d else "与基准值接近"
            print(f"\n  {speaker} → {addressee} ({stats['dialogue_count']}条):")
            print(f"    标签: {label}")
            print(f"    偏差: {delta_str}")
            print(f"    特征: 句长{stats['avg_char_count']:.0f}字, "
                  f"疑问{stats['question_ratio']*100:.0f}%, "
                  f"感叹{stats['exclamation_ratio']*100:.0f}%, "
                  f"命令{stats['command_ratio']*100:.0f}%")
            print(f"    语气词: {stats['top_particles']}")
            print(f"    代表性: 「{stats['representative_dialogues'][0][:30]}…」")

    # 关系矩阵
    matrix = {}
    for s in MAIN_CHARS:
        matrix[s] = {}
        for a in MAIN_CHARS:
            key = f"{s}→{a}"
            if key in analysis:
                matrix[s][a] = {
                    'label': analysis[key]['relationship_label'],
                    'dialogue_count': analysis[key]['dialogue_count'],
                    'avg_char_count': round(analysis[key]['avg_char_count'], 1),
                    'command_ratio': round(analysis[key]['command_ratio'], 3),
                    'exclamation_ratio': round(analysis[key]['exclamation_ratio'], 3),
                    'politeness_per_dialogue': round(analysis[key]['politeness_per_dialogue'], 3),
                    'intimate_term_ratio': round(analysis[key]['intimate_term_ratio'], 3),
                }

    # 保存
    result = {
        'source': '凉宫春日系列全13卷 对话对象分析',
        'total_dialogues': len(data),
        'baseline': {c: baseline_by_speaker.get(c, {}) for c in MAIN_CHARS},
        'per_pair_analysis': analysis,
        'relationship_matrix': matrix,
    }

    with open(OUTPUT_ANALYSIS, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {OUTPUT_ANALYSIS}")

    with open(OUTPUT_MATRIX, 'w', encoding='utf-8') as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    print(f"已保存: {OUTPUT_MATRIX}")

    # 打印关系矩阵
    print(f"\n\n=== 角色关系矩阵 ===")
    header = f"{'说话者':<10}"
    for a in MAIN_CHARS:
        header += f"{a:<14}"
    print(header)
    print("=" * 80)
    for s in MAIN_CHARS:
        row = f"{s:<10}"
        for a in MAIN_CHARS:
            if s == a:
                row += f"{'—':<14}"
            else:
                label = matrix.get(s, {}).get(a, {}).get('label', '—')
                row += f"{label:<14}"
        print(row)


if __name__ == '__main__':
    main()
