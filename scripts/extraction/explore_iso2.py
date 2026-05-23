import pycdlib, sys
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def list_dir(path, depth=0):
    indent = "  " * depth
    try:
        for child in iso.list_children(iso_path=path):
            name = child.file_identifier().decode('utf-8', errors='replace')
            if name in ['.', '..']:
                continue
            if child.is_dir():
                print(f"{indent}[DIR] {name}")
                list_dir(f"{path}/{name}", depth+1)
            else:
                size = child.get_rock_ridge_stat().st_size if child.get_rock_ridge_stat() else 0
                print(f"{indent}[FILE] {name} ({size} bytes)")
    except Exception as e:
        print(f"{indent}(Error: {e})")

list_dir('/PSP_GAME/USRDIR/data')
iso.close()
