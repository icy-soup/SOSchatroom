import pycdlib, sys, io, re
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

# Extract text from a conversation-heavy file
data = read_file_raw('/PSP_GAME/USRDIR/data/script/s_har0101.dat')

# Decode as Shift-JIS, ignoring non-text bytes
text = data.decode('shift-jis', errors='ignore')

# Print only lines with dialogue content
# The dialogue is usually between ｡ｸ (「) and ｡ｹ (」)
lines = text.split('\n')
for line in lines[:80]:
    # Clean up non-readable characters
    clean = re.sub(r'[^　-鿿＀-￯぀-ゟ゠-ヿa-zA-Z0-9「」｡ｸ｡ｹ｣\n]', '', line)
    if len(clean.strip()) > 5:
        print(clean[:200])

iso.close()
