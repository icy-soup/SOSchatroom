import pycdlib, sys, io, re, json
from collections import Counter
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

def extract_with_context(data, filename):
    """Extract ALL narrative content, not just dialogue."""
    text = data.decode('gbk', errors='replace')
    lines = text.split('\n')
    entries = []

    for line in lines:
        # Detect character dialogue (with 「」)
        dia_match = re.search(r'(har|kyo|nag|mik|koi|tur|shm)\d{6,}.*?「([^」]*)」', line)
        if dia_match:
            code = dia_match.group(1)
            q = dia_match.group(2).strip()
            name = CHAR_MAP.get(code, code)
            if len(q) >= 2:
                entries.append({'type': 'dialogue', 'speaker': name, 'text': q})
            continue

        # Detect narration - text with character code but no 「」
        # Look for text segments that aren't control characters
        for code, name in CHAR_MAP.items():
            m = re.search(r'w?' + re.escape(code) + r'\d{6,}[^\x00-\x1f]*(?!「)([^\x00-\x1f]{4,})', line)
            if m:
                narration = m.group(1).strip()
                # Filter out random binary garbage - must have at least 3 Chinese chars
                cn_chars = len(re.findall(r'[一-鿿]', narration))
                if cn_chars >= 3:
                    entries.append({'type': 'narration', 'speaker': name, 'text': narration})
                break

    return entries

# Test with a few representative files
test_files = [
    's_0000ess0.dat',  # Main story prologue
    's_0016har0.dat',  # Haruhi scene
    's_har0101.dat',   # Haruhi route chapter 1
    's_nag0101.dat',   # Nagato route chapter 1
    's_0032har0.dat',  # Another Haruhi scene
]

script_dir = '/PSP_GAME/USRDIR/data/script'

for fname in test_files:
    data = read_file_raw(f'{script_dir}/{fname}')
    entries = extract_with_context(data, fname)

    print(f"\n{'='*60}")
    print(f"=== {fname} ({len(entries)} entries) ===")
    print(f"{'='*60}")
    for e in entries[:25]:
        if e['type'] == 'dialogue':
            print(f"  [{e['speaker']}]「{e['text']}」")
        else:
            print(f"  · {e['text'][:100]}")

iso.close()
