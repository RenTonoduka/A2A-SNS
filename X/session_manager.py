"""
X Session Manager - Playwrightセッション管理
一度ログインしてセッションを保存、以降は自動復元
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from config import SESSION_DIR, BrowserConfig, LOGS_DIR

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "session.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SessionManager:
    """
    Xセッション管理クラス

    機能:
    1. 初回ログイン: ブラウザを開いて手動ログイン → セッション保存
    2. セッション復元: 保存済みセッションからログイン状態を復元
    3. セッション検証: ログイン状態の確認
    """

    X_URL = "https://x.com"
    LOGIN_URL = "https://x.com/login"

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_logged_in = False

    @property
    def session_file(self) -> Path:
        """セッションファイルパス"""
        return SESSION_DIR / f"{self.config.session_name}_session.json"

    @property
    def storage_state_file(self) -> Path:
        """Playwright storage state ファイル"""
        return SESSION_DIR / f"{self.config.session_name}_storage.json"

    def has_saved_session(self) -> bool:
        """保存済みセッションがあるか"""
        return self.storage_state_file.exists()

    async def start(self) -> "SessionManager":
        """ブラウザを起動"""
        logger.info("🚀 Starting browser...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo
        )

        # セッション復元または新規作成
        if self.has_saved_session():
            logger.info(f"📂 Restoring session from {self.storage_state_file}")
            self.context = await self.browser.new_context(
                storage_state=str(self.storage_state_file),
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
                },
                user_agent=self.config.user_agent
            )
        else:
            logger.info("🆕 Creating new session")
            self.context = await self.browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
                },
                user_agent=self.config.user_agent
            )

        self.page = await self.context.new_page()
        return self

    async def stop(self):
        """ブラウザを終了"""
        logger.info("🛑 Stopping browser...")

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    async def __aenter__(self) -> "SessionManager":
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    # ==========================================
    # ログイン関連
    # ==========================================

    async def login_interactive(self, timeout_minutes: int = 5) -> bool:
        """
        インタラクティブログイン
        ブラウザを開いてユーザーに手動ログインしてもらう
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        logger.info("🔐 Opening X login page...")
        logger.info("   Please login manually in the browser window.")
        logger.info(f"   Timeout: {timeout_minutes} minutes")

        # ログインページに移動
        await self.page.goto(self.LOGIN_URL)

        # ログイン完了を待機（ホームページにリダイレクトされるまで）
        try:
            await self.page.wait_for_url(
                f"{self.X_URL}/home",
                timeout=timeout_minutes * 60 * 1000
            )
            logger.info("✅ Login successful!")
            self._is_logged_in = True

            # セッション保存
            await self.save_session()
            return True

        except Exception as e:
            logger.error(f"❌ Login failed or timed out: {e}")
            return False

    async def verify_login(self) -> bool:
        """ログイン状態を確認"""
        if not self.page:
            return False

        try:
            await self.page.goto(self.X_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # ログインしているかどうかをチェック
            # ホームタイムラインやプロフィールアイコンの存在で判定
            is_logged_in = await self.page.locator('[data-testid="primaryColumn"]').count() > 0

            if is_logged_in:
                # 追加チェック: サイドバーのナビゲーションが表示されているか
                has_nav = await self.page.locator('[data-testid="AppTabBar_Home_Link"]').count() > 0
                is_logged_in = has_nav

            self._is_logged_in = is_logged_in
            logger.info(f"🔍 Login status: {'✅ Logged in' if is_logged_in else '❌ Not logged in'}")
            return is_logged_in

        except Exception as e:
            logger.error(f"Error verifying login: {e}")
            self._is_logged_in = False
            return False

    async def ensure_logged_in(self) -> bool:
        """
        ログイン状態を確保
        - 保存済みセッションがあれば復元して検証
        - なければインタラクティブログイン
        """
        # まず現在の状態を確認
        if await self.verify_login():
            return True

        # セッションファイルがある場合は再度試行
        if self.has_saved_session():
            logger.info("⚠️ Session exists but login verification failed.")
            logger.info("   Attempting interactive login...")

        # インタラクティブログイン
        return await self.login_interactive()

    # ==========================================
    # セッション保存・復元
    # ==========================================

    async def save_session(self):
        """現在のセッションを保存"""
        if not self.context:
            raise RuntimeError("No browser context to save")

        # Playwright storage state を保存
        await self.context.storage_state(path=str(self.storage_state_file))
        logger.info(f"💾 Session saved to {self.storage_state_file}")

        # メタデータを保存
        metadata = {
            "session_name": self.config.session_name,
            "saved_at": datetime.now().isoformat(),
            "storage_file": str(self.storage_state_file)
        }
        self.session_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        logger.info(f"📝 Session metadata saved to {self.session_file}")

    async def clear_session(self):
        """セッションをクリア"""
        if self.storage_state_file.exists():
            self.storage_state_file.unlink()
            logger.info(f"🗑️ Deleted {self.storage_state_file}")

        if self.session_file.exists():
            self.session_file.unlink()
            logger.info(f"🗑️ Deleted {self.session_file}")

        self._is_logged_in = False

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """セッション情報を取得"""
        if not self.session_file.exists():
            return None

        return json.loads(self.session_file.read_text())


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Session Manager")
    parser.add_argument("command", choices=["login", "verify", "clear", "info"],
                       help="login: ログイン, verify: 確認, clear: クリア, info: 情報表示")
    parser.add_argument("--session", default="default", help="セッション名")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード")

    args = parser.parse_args()

    config = BrowserConfig(
        session_name=args.session,
        headless=args.headless
    )

    if args.command == "info":
        manager = SessionManager(config)
        info = manager.get_session_info()
        if info:
            print("📋 Session Info:")
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print("❌ No saved session found")
        return

    if args.command == "clear":
        manager = SessionManager(config)
        await manager.clear_session()
        print("✅ Session cleared")
        return

    # ブラウザ操作が必要なコマンド
    async with SessionManager(config) as manager:
        if args.command == "login":
            print("=" * 60)
            print("🔐 X Login")
            print("=" * 60)
            print("ブラウザが開きます。手動でログインしてください。")
            print("ログイン完了後、自動的にセッションが保存されます。")
            print("=" * 60)

            success = await manager.login_interactive()
            if success:
                print("\n✅ ログイン成功！セッションが保存されました。")
            else:
                print("\n❌ ログインに失敗しました。")

        elif args.command == "verify":
            is_logged_in = await manager.verify_login()
            if is_logged_in:
                print("✅ ログイン状態: 有効")
            else:
                print("❌ ログイン状態: 無効（再ログインが必要）")


if __name__ == "__main__":
    asyncio.run(main())
