import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

base = r'F:\Extra Learning\github\haruhi-skill\reference'

# Combine all volumes
files = [
    '1-11凉宫春日物语.txt',
    '12凉宫春日物语.txt',
    '13凉宫春日物语.txt',
]

total_lines = 0
for f in files:
    path = os.path.join(base, f)
    with open(path, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()
    total_lines += len(lines)
    print(f"{f}: {len(lines)} lines")

print(f"\nTotal: {total_lines} lines")
print(f"Total dialogue markers: use grep later")
