"""从小说标注对话数据直接计算概率矩阵"""
import sys, json
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# 加载小说对话标注数据
with open(r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_annotated.json', 'r', encoding='utf-8') as f:
    dialogues = json.load(f)

print(f"总对话数: {len(dialogues)}")

# SOS团主要5角色 + 重要配角
MAIN_CHARS = ['凉宫春日', '阿虚', '长门有希', '朝比奈实玖瑠', '古泉一树']

# 过滤：只保留主要角色的对话
main = [d for d in dialogues if d['speaker'] in MAIN_CHARS]
print(f"主要角色对话: {len(main)}")

# === 1. 基础统计 ===
counts = Counter(d['speaker'] for d in main)
print(f"\n【各角色对话量】")
for name, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {name}: {n} ({n/len(main)*100:.1f}%)")

# === 2. 各卷分布 ===
vols = Counter(d.get('vol', 0) for d in main)
print(f"\n【各卷对话分布】")
for v in sorted(vols.keys()):
    print(f"  卷{v}: {vols[v]}条")

# === 3. 条件概率矩阵 ===
total_by_speaker = Counter(d['speaker'] for d in main)
transitions = Counter()

for i in range(len(main) - 1):
    curr = main[i]['speaker']
    nxt = main[i+1]['speaker']
    transitions[(curr, nxt)] += 1

print(f"\n【条件概率矩阵 P(回应|触发)%】")
header = f"{'触发→回应':<14}"
for c in MAIN_CHARS:
    header += f"{c:<12}"
print(header)
print("-" * 74)

for s in MAIN_CHARS:
    row = f"{s:<14}"
    for r in MAIN_CHARS:
        if s == r:
            row += f"{'—':<12}"
        else:
            prob = transitions.get((s, r), 0) / total_by_speaker[s] * 100 if total_by_speaker[s] > 0 else 0
            row += f"{prob:>5.1f}%    "
    print(row)

# === 4. Top回应链 ===
print(f"\n【Top 回应链】")
items = []
for s in MAIN_CHARS:
    for r in MAIN_CHARS:
        if s != r:
            prob = transitions.get((s, r), 0) / total_by_speaker[s] * 100 if total_by_speaker[s] > 0 else 0
            items.append((s, r, prob, transitions.get((s, r), 0)))
items.sort(key=lambda x: -x[2])

for s, r, p, n in items[:10]:
    print(f"  {s} → {r}: {p:.1f}% ({n}次)")

# === 5. 沉默/活跃度分析 ===
print(f"\n【对话间隔分析（沉默容忍度参考）】")
gaps = defaultdict(list)
last_pos = {}
for i, d in enumerate(main):
    s = d['speaker']
    if s in last_pos:
        gap = i - last_pos[s] - 1
        gaps[s].append(gap)
    last_pos[s] = i

for name in MAIN_CHARS:
    if name in gaps and gaps[name]:
        g = gaps[name]
        avg_gap = sum(g) / len(g)
        median_gap = sorted(g)[len(g)//2]
        max_gap = max(g)
        p_gt10 = sum(1 for x in g if x > 10) / len(g) * 100
        p_gt20 = sum(1 for x in g if x > 20) / len(g) * 100
        print(f"  {name}: 平均间隔={avg_gap:.1f}轮, 中位数={median_gap}轮, 最长沉默={max_gap}轮")
        print(f"           P(间隔>10轮)={p_gt10:.0f}%, P(间隔>20轮)={p_gt20:.0f}%")

# === 6. 保存结果 ===
BASE_PROB = {
    s: round(counts[s] / len(main), 4) for s in MAIN_CHARS
}

result = {
    'source': '凉宫春日系列全13卷 小说对话标注',
    'total_dialogues': len(main),
    'per_volume': dict(sorted(vols.items())),
    'speak_counts': dict(counts),
    'base_probability': BASE_PROB,
    'conditional_probability_matrix': {
        s: {r: round(transitions.get((s, r), 0) / total_by_speaker[s], 4) if total_by_speaker[s] > 0 else 0 for r in MAIN_CHARS}
        for s in MAIN_CHARS
    },
    'transition_counts': {f"{s}→{r}": transitions.get((s, r), 0) for s in MAIN_CHARS for r in MAIN_CHARS if s != r},
    'silence_analysis': {
        name: {
            'avg_gap_rounds': round(sum(gaps[name])/len(gaps[name]), 1),
            'median_gap': sorted(gaps[name])[len(gaps[name])//2],
            'max_gap': max(gaps[name]),
            'p_gap_gt_10': round(sum(1 for x in g if x > 10) / len(g) * 100, 1),
            'p_gap_gt_20': round(sum(1 for x in g if x > 20) / len(g) * 100, 1),
        } for name in MAIN_CHARS if name in gaps
    }
}

out_path = r'F:\Extra Learning\github\haruhi-skill\reference\novel_probability_result.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: {out_path}")
