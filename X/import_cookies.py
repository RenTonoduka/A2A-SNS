#!/usr/bin/env python3
"""
Cookie Import Tool - 通常ブラウザのCookieをPlaywrightにインポート

使い方:
1. Chrome拡張「EditThisCookie」などでX.comのCookieをJSON形式でエクスポート
2. cookies.json として保存
3. python import_cookies.py

または、Chrome/SafariのCookieデータベースから直接読み込み:
  python import_cookies.py --from-chrome
"""

import json
import sys
import os
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SESSION_DIR = SCRIPT_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)


def import_from_json(json_file: str = "cookies.json"):
    """JSONファイルからCookieをインポート"""
    json_path = SCRIPT_DIR / json_file

    if not json_path.exists():
        print(f"❌ {json_file} が見つかりません")
        print("")
        print("手順:")
        print("1. Chrome拡張「EditThisCookie」をインストール")
        print("2. X.com にログイン")
        print("3. 拡張機能アイコンをクリック → Export")
        print(f"4. {json_path} として保存")
        print("5. 再度このスクリプトを実行")
        return False

    try:
        cookies = json.loads(json_path.read_text())
        print(f"📂 Loaded {len(cookies)} cookies from {json_file}")

        # Playwrightのstorage state形式に変換
        storage_state = {
            "cookies": [],
            "origins": []
        }

        for cookie in cookies:
            # sameSite値をPlaywright互換に変換
            same_site = cookie.get("sameSite", "Lax")
            if same_site == "no_restriction":
                same_site = "None"
            elif same_site is None or same_site == "null":
                same_site = "Lax"
            elif same_site not in ("Strict", "Lax", "None"):
                same_site = "Lax"

            pw_cookie = {
                "name": cookie.get("name"),
                "value": cookie.get("value"),
                "domain": cookie.get("domain", ".x.com"),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", True),
                "httpOnly": cookie.get("httpOnly", False),
                "sameSite": same_site
            }

            # 有効期限
            if "expirationDate" in cookie:
                pw_cookie["expires"] = cookie["expirationDate"]

            storage_state["cookies"].append(pw_cookie)

        # 保存
        output_file = SESSION_DIR / "default_storage.json"
        output_file.write_text(json.dumps(storage_state, indent=2))

        print(f"✅ Saved to {output_file}")
        print("")
        print("次のステップ:")
        print("  python session_manager.py verify")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def import_from_chrome(profile: str = "Profile 5"):
    """ChromeのCookieデータベースから直接インポート（macOS）"""
    # ChromeのCookieファイルパス
    chrome_cookie_path = Path.home() / f"Library/Application Support/Google/Chrome/{profile}/Cookies"

    if not chrome_cookie_path.exists():
        print("❌ Chrome Cookieファイルが見つかりません")
        print(f"   Expected: {chrome_cookie_path}")
        return False

    # コピーを作成（Chromeが使用中の場合があるため）
    temp_cookie = SCRIPT_DIR / "temp_cookies.db"
    shutil.copy(chrome_cookie_path, temp_cookie)

    try:
        conn = sqlite3.connect(str(temp_cookie))
        cursor = conn.cursor()

        # X.comのCookieを取得
        cursor.execute("""
            SELECT name, value, host_key, path, is_secure, is_httponly, expires_utc
            FROM cookies
            WHERE host_key LIKE '%x.com%' OR host_key LIKE '%twitter.com%'
        """)

        cookies = cursor.fetchall()
        conn.close()

        if not cookies:
            print("❌ X.com のCookieが見つかりません")
            print("   Chromeで X.com にログインしてください")
            return False

        print(f"📂 Found {len(cookies)} cookies for X.com")

        # Playwright形式に変換
        storage_state = {"cookies": [], "origins": []}

        for name, value, domain, path, secure, httponly, expires in cookies:
            pw_cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": bool(secure),
                "httpOnly": bool(httponly),
                "sameSite": "Lax"
            }

            if expires:
                # Chrome epoch to Unix epoch
                pw_cookie["expires"] = (expires / 1000000) - 11644473600

            storage_state["cookies"].append(pw_cookie)

        # 保存
        output_file = SESSION_DIR / "default_storage.json"
        output_file.write_text(json.dumps(storage_state, indent=2))

        print(f"✅ Saved {len(storage_state['cookies'])} cookies to {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if temp_cookie.exists():
            temp_cookie.unlink()


def create_manual_cookie_file():
    """手動でCookieを入力するためのテンプレートを作成"""
    template = [
        {
            "name": "auth_token",
            "value": "YOUR_AUTH_TOKEN_HERE",
            "domain": ".x.com",
            "path": "/",
            "secure": True,
            "httpOnly": True
        },
        {
            "name": "ct0",
            "value": "YOUR_CT0_TOKEN_HERE",
            "domain": ".x.com",
            "path": "/",
            "secure": True,
            "httpOnly": False
        }
    ]

    template_file = SCRIPT_DIR / "cookies_template.json"
    template_file.write_text(json.dumps(template, indent=2, ensure_ascii=False))

    print(f"📝 テンプレートを作成しました: {template_file}")
    print("")
    print("手順:")
    print("1. Chrome DevTools を開く (F12)")
    print("2. Application → Cookies → https://x.com")
    print("3. 'auth_token' と 'ct0' の値をコピー")
    print("4. cookies_template.json を編集")
    print("5. cookies.json にリネーム")
    print("6. python import_cookies.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cookie Import Tool")
    parser.add_argument("--from-chrome", action="store_true", help="Chromeから直接インポート")
    parser.add_argument("--template", action="store_true", help="テンプレートファイルを作成")
    parser.add_argument("--file", default="cookies.json", help="インポートするJSONファイル")

    args = parser.parse_args()

    if args.template:
        create_manual_cookie_file()
    elif args.from_chrome:
        import_from_chrome()
    else:
        import_from_json(args.file)
