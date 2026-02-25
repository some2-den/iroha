import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. ログインしてトークン取得
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/auth/login',
    data=json.dumps({'username': 'admin', 'password': 'admin123'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
r = urllib.request.urlopen(req)
data = json.loads(r.read())
token = data['access_token']
print(f"[OK] Login: role={data['role']}")
print(f"   Token[:50]: {token[:50]}...")

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 2. 各エンドポイントをテスト
endpoints = [
    ('GET', '/api/admin/stores', 'GET /admin/stores'),
    ('GET', '/api/auth/admin/users', 'GET /auth/admin/users'),
    ('GET', '/api/au1-collection/summary', 'GET /au1-collection/summary'),
    ('GET', '/api/au1-collection/category', 'GET /au1-collection/category'),
    ('GET', '/api/au1-collection/detail', 'GET /au1-collection/detail'),
    ('GET', '/api/smartphone/unit-price', 'GET /smartphone/unit-price'),
]

for method, path, label in endpoints:
    req2 = urllib.request.Request(
        f'http://127.0.0.1:8000{path}',
        headers=headers,
        method=method
    )
    try:
        r2 = urllib.request.urlopen(req2)
        print(f"[OK] {label}: {r2.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[FAIL] {label}: {e.code} - {body[:200]}")
