import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"
results = []

def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((status, label, detail))
    print(f"[{status}] {label}" + (f" - {detail}" if detail else ""))

def get(path, token=None, expect_status=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    try:
        r = urllib.request.urlopen(req)
        return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()

def post(path, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), {}

print("=" * 60)
print("セキュリティチェック開始")
print("=" * 60)

# 1. /docs が非公開かどうか（DEBUG=true なら公開されるので今回はスキップ）
status, headers, _ = get("/docs")
check("[INFO] /docs 公開状態", True, f"status={status} (DEBUG=true時は200が正常)")

# 2. セキュリティヘッダー確認
status, headers, _ = get("/")
check("X-Content-Type-Options: nosniff", headers.get("x-content-type-options") == "nosniff", headers.get("x-content-type-options"))
check("X-Frame-Options: DENY", headers.get("x-frame-options") == "DENY", headers.get("x-frame-options"))
check("X-XSS-Protection", "x-xss-protection" in headers, headers.get("x-xss-protection"))
check("Referrer-Policy", "referrer-policy" in headers, headers.get("referrer-policy"))

# 3. 認証なしでAPIアクセス → 401
status, _, _ = get("/api/admin/stores")
check("認証なし /admin/stores → 401", status == 401, f"status={status}")
status, _, _ = get("/api/auth/admin/users")
check("認証なし /auth/admin/users → 401", status == 401, f"status={status}")
status, _, _ = get("/api/au1-collection/summary")
check("認証なし /au1-collection/summary → 401", status == 401, f"status={status}")

# 4. ログインして正常動作確認
status, _, data = post("/api/auth/login", {"username": "admin", "password": "admin123"})
token = data.get("access_token")
check("admin ログイン成功", status == 200 and token, f"status={status}")

if token:
    # 5. トークンで各エンドポイントアクセス → 200
    status, _, _ = get("/api/admin/stores", token)
    check("認証あり /admin/stores → 200", status == 200, f"status={status}")
    status, _, _ = get("/api/auth/admin/users", token)
    check("認証あり /auth/admin/users → 200", status == 200, f"status={status}")

# 6. レート制限テスト（5回以上失敗 → 429）
print("\n[TEST] レート制限テスト（失敗ログインを連続実行）...")
rate_limited = False
for i in range(7):
    status, _, _ = post("/api/auth/login", {"username": "noexist", "password": "wrong"})
    if status == 429:
        rate_limited = True
        break
check("ブルートフォース対策（429 レート制限）", rate_limited, f"5回失敗後に429を受信: {rate_limited}")

# 7. audit エンドポイントのパラメータ上限
if token:
    status, _, body = get("/api/admin/security-logs?days=99999&limit=99999", token)
    # 422 (Validation Error) が返るはず
    check("audit クエリ上限バリデーション", status == 422, f"days=99999/limit=99999 → status={status}")

print("\n" + "=" * 60)
passed = sum(1 for s,_,_ in results if s == "PASS")
failed = sum(1 for s,_,_ in results if s == "FAIL")
print(f"結果: {passed} PASS / {failed} FAIL / {len(results)} 合計")
print("=" * 60)
