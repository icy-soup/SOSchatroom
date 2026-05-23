import pycdlib, sys, io, re
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def read_file_raw(p):
    buf = io.BytesIO()
    iso.get_file_from_iso_fp(buf, iso_path=p)
    data = buf.getvalue()
    buf.close()
    return data

data = read_file_raw('/PSP_GAME/USRDIR/data/script/s_har0101.dat')
text = data.decode('gbk', errors='replace')
lines = text.split('\n')

print("=== Testing regex on each line ===")
pattern = re.compile(r'kyo\d{6,}.[^\x00-\x1f]*「([^」]*)」')
for i, line in enumerate(lines[:30]):
    m = pattern.search(line)
    if m:
        print(f"  Line {i}: MATCHED -> {m.group(1)}")
    else:
        # Show if kyo exists in line
        if 'kyo' in line:
            print(f"  Line {i}: has kyo but no match: {repr(line[:100])}")
        if 'har' in line:
            print(f"  Line {i}: has har but no match: {repr(line[:100])}")

# Try the simplest possible pattern
print("\n=== Simplest pattern test ===")
for i, line in enumerate(lines[:30]):
    m = re.search(r'kyo\d+「', line)
    if m:
        print(f"  Line {i}: kyo\\d+「 MATCHED")
    m = re.search(r'har\d+「', line)
    if m:
        print(f"  Line {i}: har\\d+「 MATCHED")

iso.close()
