import pycdlib, sys
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

# Show top-level items in data/
for child in iso.list_children(iso_path='/PSP_GAME/USRDIR/data'):
    name = child.file_identifier().decode('utf-8', errors='replace')
    if name in ['.', '..']:
        continue
    try:
        is_dir = child.is_dir()
    except:
        is_dir = False
    if is_dir:
        print(f"[DIR] {name}")
    else:
        print(f"[FILE] {name}")

# Also check for any CPK or AFS archives in data root
print("\n--- Searching for archive files ---")
for child in iso.list_children(iso_path='/PSP_GAME/USRDIR/data'):
    name = child.file_identifier().decode('utf-8', errors='replace')
    if name.lower().endswith(('.cpk', '.afs', '.arc', '.pak', '.arc', '.gzp')):
        print(f"Found archive: {name}")

# Check module directory
print("\n--- module directory ---")
try:
    for child in iso.list_children(iso_path='/PSP_GAME/USRDIR/module'):
        name = child.file_identifier().decode('utf-8', errors='replace')
        if name not in ['.', '..']:
            print(f"  {name}")
except:
    print("  (not found)")

iso.close()
