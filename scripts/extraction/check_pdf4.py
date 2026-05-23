import sys
sys.stdout.reconfigure(encoding='utf-8')
from PyPDF2 import PdfReader

path = r'F:/Extra Learning/github/haruhi-skill/reference/ChatHaruhi_ Reviving Anime Character in Reality.pdf'
reader = PdfReader(path)

for i in range(4, len(reader.pages)):
    text = reader.pages[i].extract_text()
    print(f'\n=== Page {i+1} ===')
    print(text[:3000])
