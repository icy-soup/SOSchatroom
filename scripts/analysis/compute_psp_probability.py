"""
从PSP游戏对话数据直接计算概率矩阵
PSP数据已有明确的speaker标签（11285条对话）
"""
import sys, json
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# 加载PSP对话数据
with open(r'F:\Extra Learning\github\haruhi-skill\reference\psp-game\psp_dialogues.json', 'r', encoding='utf-8') as f:
    dialogues = json.load(f)

print(f"总对话数: {len(dialogues)}")

# SOS团主要5角色
MAIN_CHARS = ['凉宫春日', '阿虚', '长门有希', '朝比奈实玖瑠', '古泉一树']

# 过滤：只保留主要角色的对话
main = [d for d in dialogues if d['speaker'] in MAIN_CHARS]
print(f"主要角色对话: {len(main)} (排除鹤屋、三味线等)")

# === 1. 基础统计 ===
counts = Counter(d['speaker'] for d in main)
print(f"\n【各角色对话量】")
for name, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {name}: {n} ({n/len(main)*100:.1f}%)")

# === 2. 条件概率矩阵 ===
total_by_speaker = Counter(d['speaker'] for d in main)
transitions = Counter()

for i in range(len(main) - 1):
    curr = main[i]['speaker']
    nxt = main[i+1]['speaker']
    if curr != nxt:
        transitions[(curr, nxt)] += 1

print(f"\n【条件概率矩阵 P(回应|触发)%】")
header = f"{'触发\\回应':<14}"
for c in MAIN_CHARS:
    header += f"{c:<14}"
print(header)
print("-" * 84)

for s in MAIN_CHARS:
    row = f"{s:<14}"
    for r in MAIN_CHARS:
        if s == r:
            row += f"{'—':<14}"
        else:
            prob = transitions.get((s, r), 0) / total_by_speaker[s] * 100
            row += f"{prob:>6.2f}%     "
    print(row)

# === 3. Top响应链 ===
print(f"\n【Top 回应链】")
items = []
for s in MAIN_CHARS:
    for r in MAIN_CHARS:
        if s != r:
            prob = transitions.get((s, r), 0) / total_by_speaker[s] * 100
            items.append((s, r, prob, transitions.get((s, r), 0)))
items.sort(key=lambda x: -x[2])

for s, r, p, n in items:
    print(f"  {s} → {r}: {p:.1f}% ({n}次)")

# === 4. 沉默/活跃度分析 ===
print(f"\n【对话间隔分析（沉默容忍度参考）】")
# 统计每个角色在对话序列中的"间隔"（多少轮别人的对话后才再次说话）
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
        print(f"  {name}: 平均间隔={avg_gap:.1f}轮, 中位数={median_gap}轮, 最长沉默={max_gap}轮")

# === 5. 保存结果 ===
result = {
    'source': 'PSP游戏 凉宫春日的约定 (CVN汉化版)',
    'total_dialogues': len(main),
    'speak_counts': dict(counts),
    'conditional_probability_matrix': {
        s: {r: round(transitions.get((s, r), 0) / total_by_speaker[s] * 100, 1) if total_by_speaker[s] > 0 else 0 for r in MAIN_CHARS}
        for s in MAIN_CHARS
    },
    'transition_counts': {f"{s}→{r}": transitions.get((s, r), 0) for s in MAIN_CHARS for r in MAIN_CHARS if s != r},
    'silence_analysis': {
        name: {
            'avg_gap_rounds': round(sum(gaps[name])/len(gaps[name]), 1),
            'median_gap': sorted(gaps[name])[len(gaps[name])//2],
            'max_gap': max(gaps[name])
        } for name in MAIN_CHARS if name in gaps
    }
}

out_path = r'F:\Extra Learning\github\haruhi-skill\reference\psp-game\probability_result.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: {out_path}")
