import requests, base64, json, os

os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'

# Chat-Haruhi-Suzumiya
r = requests.get('https://api.github.com/repos/LC1332/Chat-Haruhi-Suzumiya/readme')
data = r.json()
content = data['content']
decoded = base64.b64decode(content.replace('\n','')).decode('utf-8')
print("=== Chat-Haruhi-Suzumiya ===")
print(decoded[:10000])
print("\n\n=== 分隔线 ===\n\n")

# SillyTavern
r2 = requests.get('https://api.github.com/repos/SillyTavern/SillyTavern/readme')
data2 = r2.json()
content2 = data2['content']
decoded2 = base64.b64decode(content2.replace('\n','')).decode('utf-8')
print("=== SillyTavern ===")
print(decoded2[:5000])
