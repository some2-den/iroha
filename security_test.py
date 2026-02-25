"""
セキュリティテストスクリプト
未認証でAPIエンドポイントにアクセスできるかを検証
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

PASS = "\033[92m[PASS]\033[0m"  # 緑 = 安全
FAIL = "\033[91m[FAIL]\033[0m"  # 赤 = 脆弱性あり
WARN = "\033[93m[WARN]\033[0m"  # 黄 = 注意

results = []

def test(name, method, path, expected_status=401, **kwargs):
    """エンドポイントのセキュリティをテスト"""
    url = f"{BASE_URL}{path}"
    r = getattr(requests, method)(url, timeout=5, **kwargs)
    
    # 401/403 → アクセス拒否（安全）
    # 200/2xx → 認証なしでアクセス成功（脆弱性）
    is_vulnerable = r.status_code not in (401, 403, 404, 405, 422)
    icon = FAIL if is_vulnerable else PASS
    severity = "🔴 CRITICAL" if is_vulnerable else "✅ OK"
    
    result = {
        "name": name,
        "method": method.upper(),
        "path": path,
        "status": r.status_code,
        "vulnerable": is_vulnerable,
        "detail": ""
    }
    
    try:
        body = r.json()
        result["detail"] = str(body)[:120]
    except:
        result["detail"] = r.text[:120]
    
    results.append(result)
    print(f"{icon} [{r.status_code}] {method.upper()} {path}")
    if is_vulnerable:
        print(f"     ↳ {severity}: 未認証でアクセス可能! レスポンス: {result['detail']}")
    return r


print("=" * 70)
print("  セキュリティテスト開始 (未認証アクセステスト)")
print("=" * 70)

# ─── サーバー疎通確認 ────────────────────────────────────────────
print("\n▶ サーバー疎通確認")
r = requests.get(f"{BASE_URL}/api/health", timeout=5)
print(f"  /api/health → {r.status_code}")

# ─── 1. 売上データ系（認証なし GET）────────────────────────────────
print("\n▶ 1. 売上データ系エンドポイント（認証なしで取得できるか？）")
test("全トランザクション一覧",    "get",  "/api/transactions")
test("日別売上サマリー",          "get",  "/api/summary/daily")
test("商品別サマリー",            "get",  "/api/summary/product")
test("スタッフ一覧",              "get",  "/api/summary/staff-list")
test("スタッフ別成績",            "get",  "/api/summary/staff-performance")
test("スタッフ集計成績",          "get",  "/api/summary/staff-aggregated")
test("au+1 Collection サマリー",  "get",  "/api/au1-collection/summary")
test("au+1 Collection 詳細",      "get",  "/api/au1-collection/detail")
test("au+1 Collection カテゴリ",   "get",  "/api/au1-collection/category")
test("au+1 Collection 日別",      "get",  "/api/au1-collection/daily")
test("au+1 Collection 合計",      "get",  "/api/au1-collection/total")
test("スマートフォン単価",         "get",  "/api/smartphone/unit-price")
test("スマートフォン販売サマリー", "get",  "/api/smartphone/summary")

# ─── 2. 管理者系エンドポイント（認証なし）──────────────────────────
print("\n▶ 2. 管理者系エンドポイント（認証なしで操作できるか？）")
test("全売上データ取得（管理者）",    "get",  "/api/admin/sales-data")
test("店舗一覧取得（管理者）",        "get",  "/api/admin/stores")
test("全売上データ削除（管理者）",    "post", "/api/admin/clear-data")
test("新規店舗追加（管理者）",        "post", "/api/admin/stores",
     json={"store_code": "TEST99", "store_name": "テスト店舗", "location": "東京"})

# ─── 3. IDOR（IDを変えて他人のリソースにアクセス）──────────────────
print("\n▶ 3. IDOR（クエリパラメータにIDを渡して管理者権限を詐称）")
test("IDパラメータで管理者権限詐称（users一覧）",
     "get", "/api/auth/admin/users?admin_user_id=1")
test("IDパラメータで管理者権限詐称（セキュリティログ）",
     "get", "/api/admin/security-logs?admin_user_id=1")

# ─── 4. CSVアップロード（認証なし）───────────────────────────────
print("\n▶ 4. CSVアップロード（認証なし）")
dummy_csv = b"date,store_code,product,qty\n2026-01-01,S001,item,1\n"
r_upload = requests.post(
    f"{BASE_URL}/api/upload",
    files={"file": ("test.csv", dummy_csv, "text/csv")},
    timeout=5
)
is_vulnerable = r_upload.status_code not in (401, 403, 404, 405, 422)
icon = FAIL if is_vulnerable else PASS
print(f"{icon} [{r_upload.status_code}] POST /api/upload")
if is_vulnerable:
    print(f"     ↳ 🔴 CRITICAL: 未認証でCSVアップロード可能!")
results.append({"name": "CSVアップロード", "vulnerable": is_vulnerable, "status": r_upload.status_code})

# ─── 5. 管理者パスワード変更（現パスワードだけで変更可能）──────────
print("\n▶ 5. 管理者パスワード変更（現パスワードのみで変更可能か？）")
r_pw = requests.post(
    f"{BASE_URL}/api/admin/change-password",
    json={"old_password": "wrong_password", "new_password": "hacked"},
    timeout=5
)
print(f"  [{r_pw.status_code}] POST /api/admin/change-password (誤パスワード) → {r_pw.text[:100]}")
print(f"  {WARN} このエンドポイントはトークンなしで誰でも試行できます（ブルートフォース可）")

# ─── 結果サマリー ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  テスト結果サマリー")
print("=" * 70)

vulnerable_list = [r for r in results if r.get("vulnerable")]
safe_count = len(results) - len(vulnerable_list)

print(f"  全テスト数  : {len(results)}")
print(f"  安全        : {safe_count}")
print(f"  脆弱性あり  : \033[91m{len(vulnerable_list)}\033[0m")

if vulnerable_list:
    print("\n  🔴 脆弱なエンドポイント一覧:")
    for v in vulnerable_list:
        name = v.get("name", "")
        path = v.get("path", "")
        method = v.get("method", "")
        status = v.get("status", "")
        print(f"    - [{status}] {method} {path}  ({name})")

print("\n  主な問題:")
print("  1. Bearer Token / セッション認証が存在しない")
print("  2. 認証は user_id=1 などの整数をURLパラメータで渡すだけ（IDOR）")
print("  3. 多くのGET/POSTエンドポイントに Depends(auth) が未設定")
print("  4. /api/admin/clear-data は完全に認証なし（全データ削除可能）")
print("  5. /api/admin/* (stores) は認証なしで店舗追加・取得可能")
