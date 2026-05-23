import pycdlib, sys
sys.stdout.reconfigure(encoding='utf-8')

iso_path = r'E:\凉宫春日的约定\凉宫春日的约定\cvn-smhny_V1.1.iso'

try:
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)

    print("ISO Format:", iso.get_udf_volume_identifier() if iso.has_udf() else "Standard ISO9660")

    # List files
    count = 0
    for child in iso.list_children(iso_path='/'):
        print(f"  {child.file_identifier()}")
        count += 1
        if count > 50:
            print("  ... (truncated)")
            break

    # Try PSP directory
    print("\n--- PSP_GAME directory ---")
    for child in iso.list_children(iso_path='/PSP_GAME'):
        print(f"  {child.file_identifier()}")

    print("\n--- PSP_GAME/USRDIR ---")
    for child in iso.list_children(iso_path='/PSP_GAME/USRDIR'):
        print(f"  {child.file_identifier()}")

    iso.close()
except Exception as e:
    print(f"Error: {e}")
