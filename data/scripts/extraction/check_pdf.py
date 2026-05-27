import fitz
doc = fitz.open(r'F:/Extra Learning/github/haruhi-skill/reference/ChatHaruhi_ Reviving Anime Character in Reality.pdf')
print('Pages:', len(doc))
print('Encrypted:', doc.is_encrypted)
if doc.is_encrypted:
    if doc.authenticate(''):
        print('Empty password worked, extracting...')
    else:
        print('Password required')
        print('Trying "ChatHaruhi"...')
        if doc.authenticate('ChatHaruhi'):
            print('Password ChatHaruhi worked!')
        else:
            print('Failed')
            raise Exception("Cannot decrypt")
for i, page in enumerate(doc):
    text = page.get_text()
    print(f'\n=== Page {i+1} ===')
    print(text[:3000])
