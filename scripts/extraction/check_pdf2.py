from PyPDF2 import PdfReader

path = r'F:/Extra Learning/github/haruhi-skill/reference/ChatHaruhi_ Reviving Anime Character in Reality.pdf'
reader = PdfReader(path)
print("Encrypted:", reader.is_encrypted)

if reader.is_encrypted:
    for pwd in ['', 'ChatHaruhi', 'haruhi', 'chat-haruhi', '123', 'password']:
        try:
            reader.decrypt(pwd)
            page = reader.pages[0]
            text = page.extract_text()
            if text.strip():
                print(f"Password '{pwd}' worked!")
                print("First page text:", text[:500])
                break
        except:
            continue
    else:
        print("None of the common passwords worked")
else:
    for i, page in enumerate(reader.pages):
        print(f"\n=== Page {i+1} ===")
        print(page.extract_text()[:3000])
