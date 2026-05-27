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

def extract_dialogues(data, filename):
    text = data.decode('gbk', errors='replace')
    lines = text.split('\n')
    results = []
    for line in lines:
        for code, name in CHAR_MAP.items():
            m = re.match(r'^[a-z]*' + code + r'\d{6,}(.*)', line)
            if m:
                after = m.group(1)
                quoted = re.findall(r'「([^」]*)」', after)
                for q in quoted:
                    q = q.strip()
                    if len(q) >= 2:
                        results.append({'speaker': name, 'text': q, 'file': filename})
                break
    return results

# Collect all .dat files
script_dir = '/PSP_GAME/USRDIR/data/script'
dat_files = []
for child in iso.list_children(iso_path=script_dir):
    name = child.file_identifier().decode('utf-8', errors='replace')
    if name in ['.', '..']:
        continue
    if name.endswith('.dat'):
        dat_files.append(name)

dat_files.sort()
print(f"Total .dat files: {len(dat_files)}")

all_data = []
count = 0
for dat in dat_files:
    try:
        data = read_file_raw(f'{script_dir}/{dat}')
        dialogues = extract_dialogues(data, dat)
        all_data.extend(dialogues)
        count += 1
        if count % 50 == 0:
            print(f"  processed {count}/{len(dat_files)} files, {len(all_data)} dialogues so far...")
    except:
        pass

print(f"\nTotal dialogues: {len(all_data)}")

# Save JSON
out_json = r'F:\Extra Learning\github\haruhi-skill\reference\psp_dialogues.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print(f"Saved JSON: {out_json}")

# Save readable text version per character
out_txt = r'F:\Extra Learning\github\haruhi-skill\reference\psp_dialogues.txt'
with open(out_txt, 'w', encoding='utf-8') as f:
    for d in all_data:
        f.write(f"[{d['speaker']}]「{d['text']}」\n")
print(f"Saved text: {out_txt}")

# Stats
from collections import Counter
stats = Counter(d['speaker'] for d in all_data)
print("\n=== Per character ===")
for name, n in stats.most_common():
    print(f"  {name}: {n}")

iso.close()
