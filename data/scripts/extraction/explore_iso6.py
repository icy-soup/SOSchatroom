import pycdlib, sys
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def list_dir(path, depth=0):
    indent = "  " * depth
    try:
        children = list(iso.list_children(iso_path=path))
        for child in children:
            name = child.file_identifier().decode('utf-8', errors='replace')
            if name in ['.', '..']:
                continue
            try:
                is_dir = child.is_dir()
            except:
                is_dir = False
            if is_dir:
                print(f"{indent}[DIR] {name}/")
                if depth < 1:
                    list_dir(f"{path}/{name}", depth+1)
            else:
                print(f"{indent}[FILE] {name}")
    except Exception as e:
        print(f"{indent}(Error: {e})")

print("=== script/ ===")
list_dir('/PSP_GAME/USRDIR/data/script')

print("\n=== system/ ===")
list_dir('/PSP_GAME/USRDIR/data/system')

iso.close()
