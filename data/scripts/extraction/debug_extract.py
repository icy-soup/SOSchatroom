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

# Test with one known-working file
data = read_file_raw('/PSP_GAME/USRDIR/data/script/s_har0101.dat')
text = data.decode('gbk', errors='replace')
lines = text.split('\n')

print(f"File: s_har0101.dat, {len(lines)} lines")
print("First 20 lines raw:")
for i, line in enumerate(lines[:20]):
    print(f"  {i}: {repr(line[:150])}")

# Try simpler pattern
print("\n\nTrying simpler pattern 'kyo'...")
for i, line in enumerate(lines[:30]):
    if 'kyo' in line or 'har' in line:
        print(f"  {i}: {line[:200]}")

iso.close()
