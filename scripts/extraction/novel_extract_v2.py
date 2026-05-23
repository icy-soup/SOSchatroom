"""
从小说13卷提取对话 - v2
策略：
  1. 用Claude对文本的语义理解来识别说话者
  2. Python脚本负责分块调用 + 汇总统计
  3. 这里的代码搭建框架，由Claude逐段处理文本
"""
import sys, re, json, os
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# ===== 角色名称 =====
CHARACTERS = ['凉宫春日', '阿虚', '长门有希', '朝比奈实玖瑠', '古泉一树', '鹤屋', '朝仓凉子']

def load_text(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def save_dialogues(dialogues, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dialogues, f, ensure_ascii=False, indent=2)

def compute_matrix(dialogues):
    """从对话列表计算概率矩阵"""
    # 过滤未知说话者
    valid = [d for d in dialogues if d['speaker'] in CHARACTERS]

    counts = Counter(d['speaker'] for d in valid)
    chars = sorted(counts.keys())

    # 转移计数
    trans = Counter()
    for i in range(len(valid) - 1):
        c, n = valid[i]['speaker'], valid[i+1]['speaker']
        if c != n:
            trans[(c, n)] += 1

    # 条件概率
    matrix = {}
    for s in chars:
        total = counts[s]
        matrix[s] = {}
        for r in chars:
            matrix[s][r] = round(trans.get((s, r), 0) / total * 100, 1) if s != r else 0

    return matrix, counts, chars

def print_results(matrix, counts, chars):
    print(f"\n【各角色对话量】")
    for name, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {name}: {n}")

    print(f"\n【条件概率矩阵 P(回应|触发)%】")
    header = f"{'触发\\回应':<12}"
    for c in chars:
        header += f"{c:<12}"
    print(header)
    for s in chars:
        row = f"{s:<12}"
        for r in chars:
            v = matrix[s].get(r, 0)
            row += f"{v:>5.1f}%    " if v > 0 else f"{'—':<12}"
        print(row)

    print(f"\n【Top 10 回应链】")
    items = []
    for s in chars:
        for r in chars:
            if s != r and matrix[s].get(r, 0) > 0:
                items.append((s, r, matrix[s][r]))
    items.sort(key=lambda x: -x[2])
    for s, r, p in items[:10]:
        print(f"  {s} → {r}: {p}%")

# ===== 以下是逐段处理的对话数据 =====
# 我会逐段读取文本并用语义理解来标注说话者
# 每个chunk处理完后追加到这里

if __name__ == '__main__':
    # 测试：读取现有结果
    result_path = r'F:\Extra Learning\github\haruhi-skill\reference\novel_dialogues_annotated.json'
    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)
        print(f"已加载 {len(dialogues)} 条标注对话")
        matrix, counts, chars = compute_matrix(dialogues)
        print_results(matrix, counts, chars)
