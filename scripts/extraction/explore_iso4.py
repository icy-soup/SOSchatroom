import pycdlib, sys
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'
iso = pycdlib.PyCdlib()
iso.open(iso_path)

def list_dir(path, depth=0):
    if depth > 4:
        return
    indent = "  " * depth
    try:
        children = list(iso.list_children(iso_path=path))
        dirs = []
        files = []
        for child in children:
            name = child.file_identifier().decode('utf-8', errors='replace')
            if name in ['.', '..']:
                continue
            try:
                is_dir = child.is_dir()
            except:
                is_dir = False
            if is_dir:
                dirs.append(name)
            else:
                files.append(name)

        for d in sorted(dirs):
            print(f"{indent}[DIR] {d}/")
            list_dir(f"{path}/{d}", depth+1)
        for f in sorted(files):
            ext = f.split('.')[-1].lower() if '.' in f else ''
            if ext in ['dat', 'bin', 'mpb']:
                print(f"{indent}[{ext.upper()}] {f}")
            else:
                print(f"{indent}      {f}")
    except Exception as e:
        print(f"{indent}(Error: {e})")

list_dir('/PSP_GAME/USRDIR/data')
iso.close()
