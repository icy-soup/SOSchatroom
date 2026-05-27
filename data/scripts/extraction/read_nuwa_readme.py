import json, base64, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'F:\Extra Learning\github\haruhi-skill\aris\nuwa_readme.json', encoding='utf-8') as f:
    d = json.load(f)

content = base64.b64decode(d['content']).decode('utf-8')
print(content[:5000])
