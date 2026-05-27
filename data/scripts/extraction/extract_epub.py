import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from ebooklib import epub
from bs4 import BeautifulSoup

def extract_epub_text(epub_path):
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:  # DOCUMENT type
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text()
            texts.append(text)
    return '\n'.join(texts)

base = r'F:\Extra Learning\github\haruhi-skill\reference'

# Extract volume 12
v12_text = extract_epub_text(os.path.join(base, '12凉宫春日物语 凉宫春日的直觉.epub'))
v12_path = os.path.join(base, '12凉宫春日物语.txt')
with open(v12_path, 'w', encoding='utf-8') as f:
    f.write(v12_text)
print(f"卷12: {len(v12_text)} chars, saved to 12凉宫春日物语.txt")

# Extract volume 13
v13_text = extract_epub_text(os.path.join(base, '13凉宫春日物语_凉宫春日剧场.epub'))
v13_path = os.path.join(base, '13凉宫春日物语.txt')
with open(v13_path, 'w', encoding='utf-8') as f:
    f.write(v13_text)
print(f"卷13: {len(v13_text)} chars, saved to 13凉宫春日物语.txt")

# Quick content check
for name in ['凉宫春日', '阿虚', '长门', '朝比奈', '实玖瑠', '古泉', '鹤屋']:
    c12 = v12_text.count(name)
    c13 = v13_text.count(name)
    if c12 > 0 or c13 > 0:
        print(f"  {name}: 卷12={c12}, 卷13={c13}")
