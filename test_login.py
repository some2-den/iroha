import urllib.request, json

for user, pw in [('admin', 'admin123'), ('manage', 'manage')]:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/auth/login',
        data=json.dumps({'username': user, 'password': pw}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        r = urllib.request.urlopen(req)
        d = json.loads(r.read())
        print(f'{user} ログイン: OK, role={d.get("role")}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f'{user} ログイン: FAIL {e.code} {body}')
    except Exception as e:
        print(f'接続エラー: {e}')
