"""
Google OAuth2 認証マネージャー
Gmail, Chat, Calendar API用
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# 認証ファイルのパス
AUTH_DIR = Path(__file__).parent / "config"
TOKEN_FILE = AUTH_DIR / "token.pickle"
CREDENTIALS_FILE = AUTH_DIR / "credentials.json"

# 必要なスコープ
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',           # Gmail送信
    'https://www.googleapis.com/auth/gmail.readonly',       # Gmail読み取り
    'https://www.googleapis.com/auth/chat.messages',        # Chat送信
    'https://www.googleapis.com/auth/chat.spaces.readonly', # Chat読み取り
    'https://www.googleapis.com/auth/calendar',             # Calendar操作
    'https://www.googleapis.com/auth/calendar.events',      # イベント操作
]


def get_credentials(scopes: Optional[List[str]] = None) -> Optional[Credentials]:
    """
    Google API認証情報を取得

    初回実行時はブラウザでOAuth認証が必要
    """
    scopes = scopes or SCOPES
    creds = None

    # 保存済みトークンがあれば読み込み
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # トークンが無効または期限切れの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # リフレッシュトークンで更新
            creds.refresh(Request())
        else:
            # 新規認証フロー
            if not CREDENTIALS_FILE.exists():
                print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ credentials.json が見つかりません

セットアップ手順:
1. Google Cloud Console (https://console.cloud.google.com) にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「認証情報」
4. 「認証情報を作成」→「OAuthクライアントID」
5. アプリケーションの種類: 「デスクトップアプリ」
6. JSONをダウンロードして以下に配置:
   {CREDENTIALS_FILE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), scopes
            )
            creds = flow.run_local_server(port=0)

        # トークンを保存
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print(f"✅ トークンを保存しました: {TOKEN_FILE}")

    return creds


def clear_credentials():
    """保存済み認証情報を削除"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print(f"✅ トークンを削除しました: {TOKEN_FILE}")


def check_auth_status() -> dict:
    """認証状態を確認"""
    status = {
        "credentials_file": CREDENTIALS_FILE.exists(),
        "token_file": TOKEN_FILE.exists(),
        "authenticated": False,
        "scopes": []
    }

    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
                status["authenticated"] = creds.valid
                status["scopes"] = creds.scopes or []
                if creds.expired:
                    status["authenticated"] = False
                    status["expired"] = True
        except Exception as e:
            status["error"] = str(e)

    return status


# テスト
if __name__ == "__main__":
    print("=" * 60)
    print("Google OAuth2 認証マネージャー")
    print("=" * 60)

    print("\n[1] 認証状態を確認")
    status = check_auth_status()
    print(f"  credentials.json: {'✅' if status['credentials_file'] else '❌'}")
    print(f"  token.pickle: {'✅' if status['token_file'] else '❌'}")
    print(f"  認証済み: {'✅' if status['authenticated'] else '❌'}")

    if status.get("scopes"):
        print(f"  スコープ: {len(status['scopes'])}個")

    print("\n[2] 認証を実行")
    creds = get_credentials()
    if creds:
        print("✅ 認証成功")
    else:
        print("❌ 認証失敗")

    print("\n" + "=" * 60)
