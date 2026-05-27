import pycdlib, sys, io, re, os
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def read_file_raw(iso_path_in_iso):
    buf = io.BytesIO()
    iso.get_file_from_iso_fp(buf, iso_path=iso_path_in_iso)
    data = buf.getvalue()
    buf.close()
    return data

# Character name mapping
char_map = {
    'har': '凉宫春日',
    'kyo': '阿虚',
    'nag': '长门有希',
    'mik': '朝比奈实玖瑠',
    'koi': '古泉一树',
    'tur': '鹤屋',
    'shm': '三味线',
    'ess': '剧情',
    'etc': '其他',
}

def extract_dialogues_from_script(data):
    """Extract speaker+dialogue from PSP script binary."""
    text = data.decode('shift-jis', errors='replace')
    lines = text.split('\n')
    dialogues = []

    for line in lines:
        # Find speaker prefix (3-letter code + digits)
        for code, name in char_map.items():
            pattern = code + r'\d{6,}'
            match = re.search(pattern, line)
            if match:
                speaker_id = match.group()
                # Extract dialogue text after speaker ID
                after_speaker = line[match.end():]
                # Find text between ｡ｸ (「) and ｡ｹ (」)
                dia_match = re.search(r'｡ｸ(.+?)｡ｹ', after_speaker)
                if dia_match:
                    dialogue = dia_match.group(1)
                    # Clean up garbage characters
                    dialogue = re.sub(r'[^　-鿿＀-￯぀-ゟ゠-ヿa-zA-Z0-9\.,!?、。！？—…]', '', dialogue)
                    if len(dialogue) > 3:
                        dialogues.append(f"[{name}] {dialogue}")
                break

    return dialogues

# Test with a few key files
test_files = [
    '/PSP_GAME/USRDIR/data/script/s_har0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_nag0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_0000ess0.dat',
    '/PSP_GAME/USRDIR/data/script/s_0016har0.dat',
]

all_dialogues = []
for f in test_files:
    data = read_file_raw(f)
    dialogues = extract_dialogues_from_script(data)
    all_dialogues.append(f"\n=== {f.split('/')[-1]} ({len(dialogues)} dialogues) ===")
    all_dialogues.extend(dialogues[:20])

# Save to file
output_path = r'F:\Extra Learning\github\haruhi-skill\reference\psp_dialogues_sample.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(all_dialogues))

print(f"Saved to {output_path}")
print(f"Total lines: {len(all_dialogues)}")
print("\nPreview:")
print('\n'.join(all_dialogues[:30]))

iso.close()
