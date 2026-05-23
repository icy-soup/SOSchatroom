import pycdlib, sys, io, re, json
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

CHAR_MAP = {
    'har': '凉宫春日', 'kyo': '阿虚', 'nag': '长门有希',
    'mik': '朝比奈实玖瑠', 'koi': '古泉一树',
    'tur': '鹤屋', 'shm': '三味线',
}

def read_file_raw(p):
    buf = io.BytesIO()
    iso.get_file_from_iso_fp(buf, iso_path=p)
    data = buf.getvalue()
    buf.close()
    return data

def extract_full(data, filename):
    """Extract ALL text content: dialogue + narration."""
    text = data.decode('gbk', errors='replace')
    lines = text.split('\n')
    entries = []

    for line_no, line in enumerate(lines):
        # Strategy: find lines that contain readable Chinese text
        # and determine if they're character dialogue or narration

        # Check for dialogue first: code + ... + 「」
        m = re.search(r'(har|kyo|nag|mik|koi|tur|shm)\d{6,}.*?「([^」]*)」', line)
        if m:
            q = m.group(2).strip()
            if len(q) >= 1:
                entries.append({
                    'type': 'dialogue',
                    'speaker': CHAR_MAP.get(m.group(1), m.group(1)),
                    'text': q,
                    'line': line_no
                })
                continue

        # Check for narration: w prefix + code + Chinese text (no 「」)
        m = re.search(r'w(har|kyo|nag|mik|koi|tur|shm)\d{6,}[^\x00-\x1f]*?([^\x00-\x1f]{4,})', line)
        if m:
            narration = m.group(2).strip()
            cn = len(re.findall(r'[一-鿿]', narration))
            if cn >= 3:
                entries.append({
                    'type': 'narration',
                    'speaker': CHAR_MAP.get(m.group(1), m.group(1)),
                    'text': narration,
                    'line': line_no
                })
                continue

    return entries

# Process a few key story files to show as samples
script_dir = '/PSP_GAME/USRDIR/data/script'

# Pick files that likely form coherent scenes
scene_files = [
    ('s_0000ess0.dat', '序章：咖啡厅对话'),
    ('s_0016har0.dat', '活动室日常（春日线）'),
    ('s_0032har0.dat', '电影拍摄/棒球场景'),
    ('s_har0101.dat', '春日路线·第一章'),
    ('s_nag0101.dat', '长门路线·第一章'),
    ('s_mik0101.dat', '实玖瑠路线·第一章'),
    ('s_koi0101.dat', '古泉路线·第一章'),
]

out_path = r'F:\Extra Learning\github\haruhi-skill\reference\psp_full_scenes.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    for fname, scene_name in scene_files:
        data = read_file_raw(f'{script_dir}/{fname}')
        entries = extract_full(data, fname)

        f.write(f"\n{'='*60}\n")
        f.write(f"场景：{scene_name}（{fname}，{len(entries)}条）\n")
        f.write(f"{'='*60}\n")

        for e in entries[:40]:
            if e['type'] == 'narration':
                f.write(f"  （{e['speaker']}的旁白）{e['text']}\n")
            else:
                f.write(f"  [{e['speaker']}]「{e['text']}」\n")

        if len(entries) > 40:
            f.write(f"  ...（还有{len(entries)-40}条）\n")

print(f"已保存到 {out_path}")
print("预览第一个场景：")

# Also print first scene for quick check
data = read_file_raw(f'{script_dir}/{scene_files[0][0]}')
entries = extract_full(data, scene_files[0][0])
for e in entries[:25]:
    if e['type'] == 'narration':
        print(f"  （旁白）{e['text']}")
    else:
        print(f"  [{e['speaker']}]「{e['text']}」")

iso.close()
