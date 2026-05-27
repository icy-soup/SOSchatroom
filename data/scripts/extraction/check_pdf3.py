import sys
from PyPDF2 import PdfReader

path = r'F:/Extra Learning/github/haruhi-skill/reference/ChatHaruhi_ Reviving Anime Character in Reality.pdf'
reader = PdfReader(path)

for i in range(4, len(reader.pages)):
    text = reader.pages[i].extract_text()
    # Replace problematic characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    print(f'\n=== Page {i+1} ===')
    print(text[:3000])
