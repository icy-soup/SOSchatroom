import pycdlib, sys, io, re, os, json
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

# Character ID mapping
CHAR_MAP = {
    'har': '凉宫春日', 'kyo': '阿虚', 'nag': '长门有希',
    'mik': '朝比奈实玖瑠', 'koi': '古泉一树',
    'tur': '鹤屋', 'shm': '三味线',
}
REVERSE_MAP = {v: k for k, v in CHAR_MAP.items()}

def read_file_raw(iso_path_in_iso):
    buf = io.BytesIO()
    iso.get_file_from_iso_fp(buf, iso_path=iso_path_in_iso)
    data = buf.getvalue()
    buf.close()
    return data

def extract_dialogues_from_script(data, filename):
    """Extract speaker+dialogue from PSP script binary (Chinese GBK)."""
    text = data.decode('gbk', errors='replace')
    lines = text.split('\n')
    dialogues = []
    current_narration = ""

    for line in lines:
        # Try to match character-code prefix like: kyo001010010, har0016100010
        for code, name in CHAR_MAP.items():
            # Match: optional prefix chars (w, i, b etc) + 3-letter code + digits + optional suffix
            pattern = r'^[a-z]*' + re.escape(code) + r'\d{6,}'
            match = re.match(pattern, line)
            if match:
                speaker_id = match.group()
                # Everything after speaker ID
                after = line[match.end():]
                # Extract quoted text: 「...」
                quoted = re.findall(r'「([^」]*)」', after)
                if quoted:
                    for q in quoted:
                        q = q.strip()
                        if len(q) >= 2:
                            dialogues.append({
                                'speaker': name,
                                'text': q,
                                'file': filename,
                                'speaker_id': speaker_id,
                            })
                break

    return dialogues

# Collect all .dat files in script/ directory
script_dir = '/PSP_GAME/USRDIR/data/script'
dat_files = []
for child in iso.list_children(iso_path=script_dir):
    name = child.file_identifier().decode('utf-8', errors='replace')
    if name in ['.', '..']: continue
    if name.endswith('.dat') and not name.startswith('s_cg') and not name.startswith('s_t'):
        dat_files.append(name)

dat_files.sort()
print(f"Found {len(dat_files)} script .dat files to process")

all_dialogues = []
for dat in dat_files:
    path = f'{script_dir}/{dat}'
    try:
        data = read_file_raw(path)
        dialogues = extract_dialogues_from_script(data, dat)
        all_dialogues.extend(dialogues)
    except Exception as e:
        print(f"  Error {dat}: {e}")

print(f"\nTotal dialogues extracted: {len(all_dialogues)}")

# Per-character stats
char_counts = {}
for d in all_dialogues:
    name = d['speaker']
    char_counts[name] = char_counts.get(name, 0) + 1

print("\n=== Dialogue counts per character ===")
for name, count in sorted(char_counts.items(), key=lambda x: -x[1]):
    print(f"  {name}: {count} dialogues")

# Build transition matrix
# Look at who speaks after whom
transitions = {}  # (speaker_A, speaker_B) -> count
for i in range(len(all_dialogues) - 1):
    curr = all_dialogues[i]['speaker']
    next_s = all_dialogues[i + 1]['speaker']
    if curr != next_s:
        key = (curr, next_s)
        transitions[key] = transitions.get(key, 0) + 1

print("\n=== Transition counts (who responds to whom) ===")
for (a, b), count in sorted(transitions.items(), key=lambda x: -x[1]):
    print(f"  {a} → {b}: {count}")

# Calculate conditional probability matrix
characters = sorted(char_counts.keys())
print("\n=== Conditional Probability Matrix P(row|col) ===")
print(f"{'':12s}", end='')
for col in characters:
    print(f"{col:12s}", end='')
print()

# Count total times each character speaks
total_speaks = char_counts

for row in characters:
    print(f"{row:12s}", end='')
    for col in characters:
        if row == col:
            print(f"{'—':12s}", end='')
        else:
            # P(row speaks | col just spoke)
            key = (col, row)
            count = transitions.get(key, 0)
            col_total = total_speaks.get(col, 1)
            prob = count / col_total * 100
            print(f"{prob:5.1f}%    ", end='')
    print()

# Save dialogues to reference
output_path = r'F:\Extra Learning\github\haruhi-skill\reference\psp_all_dialogues.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_dialogues, f, ensure_ascii=False, indent=2)
print(f"\nSaved to {output_path}")

# Also generate chapter sequences for each route
print("\n=== Files by character route ===")
route_files = {}
for dat in dat_files:
    route = dat.split('_')[1][:3] if '_' in dat else 'ess'
    route_name = CHAR_MAP.get(route, f'other_{route}')
    if route_name not in route_files:
        route_files[route_name] = []
    route_files[route_name].append(dat)

for route, files in sorted(route_files.items()):
    print(f"  {route}: {len(files)} files")

iso.close()
