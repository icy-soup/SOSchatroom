import pycdlib, sys, os
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def extract_file_text(iso_path_in_iso, max_bytes=5000):
    """Extract raw bytes from a file in the ISO and try to decode text."""
    try:
        fd = iso.open_file(iso_path=iso_path_in_iso)
        data = fd.read(max_bytes)
        fd.close()

        # Try to find readable text (Shift-JIS for PSP Japanese games)
        # Extract sequences of printable ASCII + Japanese characters
        text_parts = []
        current = b''

        # Try Shift-JIS decode
        try:
            text = data.decode('shift-jis', errors='replace')
        except:
            text = data.decode('utf-8', errors='replace')

        return text[:2000]
    except Exception as e:
        return f"[Error: {e}]"

# Try a few different script files
samples = [
    '/PSP_GAME/USRDIR/data/script/s_0000ess0.dat',
    '/PSP_GAME/USRDIR/data/script/s_har0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_nag0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_mik0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_koi0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_tur0101.dat',
    '/PSP_GAME/USRDIR/data/script/s_0012nag0.dat',
    '/PSP_GAME/USRDIR/data/script/s_0016har0.dat',
]

for s in samples:
    print(f"\n=== {s} ===")
    text = extract_file_text(s, 3000)
    print(text[:1500])

iso.close()
