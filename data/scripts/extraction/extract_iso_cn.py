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

def try_decode(data):
    """Try different encodings and return the one with most Chinese chars."""
    results = []
    for enc in ['gbk', 'gb2312', 'gb18030', 'utf-8', 'shift-jis']:
        try:
            text = data.decode(enc, errors='replace')
            # Count Chinese characters
            cn_chars = len(re.findall(r'[一-鿿]', text))
            results.append((cn_chars, enc, text[:500]))
        except:
            results.append((0, enc, ''))
    results.sort(reverse=True)
    return results[0]

# Test with script files that likely have dialogue
test_files = [
    '/PSP_GAME/USRDIR/data/script/s_har0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_nag0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_mik0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_koi0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_tur0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_0000ess0.dat',
    '/PSP_GAME/USRDIR/data/script/s_0016har0.dat',
]

for f in test_files:
    data = read_file_raw(f)
    cn_count, encoding, sample = try_decode(data)
    print(f"\n=== {f.split('/')[-1]} ===")
    print(f"Best encoding: {encoding} ({cn_count} Chinese chars)")
    # Show readable text
    text = data.decode(encoding, errors='replace')
    # Extract text between common quote styles
    # Chinese PSP games often use standard quotes or brackets
    lines = text.split('\n')
    readable = []
    for line in lines[:30]:
        clean = re.sub(r'[^一-鿿　-〿＀-￯ -~「」【】\n]', '', line)
        if len(clean) > 5:
            readable.append(clean[:150])
    for r in readable[:15]:
        print(f"  {r}")

iso.close()
