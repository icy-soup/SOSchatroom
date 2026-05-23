import pycdlib, sys, io
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def read_file(iso_path_in_iso, max_bytes=5000):
    try:
        buf = io.BytesIO()
        iso.get_file_from_iso_fp(buf, iso_path=iso_path_in_iso)
        data = buf.getvalue()[:max_bytes]
        buf.close()

        # Try to decode as Shift-JIS (common for PSP Japanese games)
        text = data.decode('shift-jis', errors='replace')
        # Filter to readable portions
        lines = text.split('\n')
        readable = [l for l in lines if any(c.isalpha() for c in l)]
        return '\n'.join(readable[:50])
    except Exception as e:
        return f"[Error: {e}]"

# Test a few key files
print("=== s_0000ess0.dat ===")
print(read_file('/PSP_GAME/USRDIR/data/script/s_0000ess0.dat')[:2000])

print("\n=== s_har0101.dat ===")
print(read_file('/PSP_GAME/USRDIR/data/script/s_har0101.dat')[:2000])

print("\n=== s_0016har0.dat (scene 16 Haruhi) ===")
print(read_file('/PSP_GAME/USRDIR/data/script/s_0016har0.dat')[:2000])

iso.close()
