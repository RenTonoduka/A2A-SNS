#!/usr/bin/env python3
"""
X Buzz Monitor - 自動実行スクリプト
accounts.json のアカウントリストを自動監視してバズポストを検出

使用方法:
  # デーモンとして起動（バックグラウンド実行）
  python auto_monitor.py start

  # フォアグラウンド実行
  python auto_monitor.py run

  # 1回だけチェック
  python auto_monitor.py check

  # ステータス確認
  python auto_monitor.py status

  # 停止
  python auto_monitor.py stop
"""

import os
import sys
import json
import asyncio
import signal
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# パス設定
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import DATA_DIR, LOGS_DIR
from monitor import BuzzMonitor, MonitorConfig
from notifier import BuzzNotifier

# ログ設定
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "auto_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# PIDファイル
PID_FILE = LOGS_DIR / "auto_monitor.pid"
STATUS_FILE = LOGS_DIR / "auto_monitor_status.json"


def load_accounts() -> list:
    """accounts.json からアカウントリストを読み込み"""
    accounts_file = SCRIPT_DIR / "accounts.json"

    if not accounts_file.exists():
        logger.error("accounts.json not found")
        return []

    try:
        data = json.loads(accounts_file.read_text())
        accounts = data.get("accounts", [])

        # 有効なアカウントのみ抽出
        enabled_accounts = [
            acc["username"] for acc in accounts
            if acc.get("enabled", True)
        ]

        logger.info(f"Loaded {len(enabled_accounts)} accounts from accounts.json")
        return enabled_accounts
    except Exception as e:
        logger.error(f"Error loading accounts.json: {e}")
        return []


def load_settings() -> dict:
    """accounts.json から設定を読み込み"""
    accounts_file = SCRIPT_DIR / "accounts.json"

    default_settings = {
        "default_max_posts": 50,
        "default_interval_minutes": 30,
        "rate_limit_delay_seconds": 5
    }

    try:
        data = json.loads(accounts_file.read_text())
        return data.get("settings", default_settings)
    except:
        return default_settings


def load_category_thresholds() -> dict:
    """カテゴリ別のバズ閾値を読み込み"""
    accounts_file = SCRIPT_DIR / "accounts.json"

    try:
        data = json.loads(accounts_file.read_text())
        categories = data.get("categories", {})
        return {cat: info.get("buzz_threshold", 500) for cat, info in categories.items()}
    except:
        return {}


def get_account_category(username: str) -> Optional[str]:
    """アカウントのカテゴリを取得"""
    accounts_file = SCRIPT_DIR / "accounts.json"

    try:
        data = json.loads(accounts_file.read_text())
        for acc in data.get("accounts", []):
            if acc["username"] == username:
                return acc.get("category")
    except:
        pass
    return None


def save_status(status: dict):
    """ステータスを保存"""
    status["last_updated"] = datetime.now().isoformat()
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2))


def load_status() -> dict:
    """ステータスを読み込み"""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except:
            pass
    return {}


def is_running() -> bool:
    """プロセスが実行中かチェック"""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # プロセス存在確認
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def write_pid():
    """PIDファイルを書き込み"""
    PID_FILE.write_text(str(os.getpid()))


def remove_pid():
    """PIDファイルを削除"""
    if PID_FILE.exists():
        PID_FILE.unlink()


class AutoMonitor:
    """
    自動モニタリングシステム

    accounts.json のアカウントリストを定期的に監視し、
    バズポストを検出・保存します。
    """

    def __init__(self):
        self.accounts = load_accounts()
        self.settings = load_settings()
        self.category_thresholds = load_category_thresholds()
        self.running = False
        self.monitor: Optional[BuzzMonitor] = None

        # デフォルト閾値（カテゴリ別の最小値を使用）
        if self.category_thresholds:
            self.default_threshold = min(self.category_thresholds.values())
        else:
            self.default_threshold = 500

        # 通知システム
        self.notifier = BuzzNotifier()

    def create_monitor(self) -> BuzzMonitor:
        """モニターインスタンスを作成"""
        config = MonitorConfig(
            target_accounts=self.accounts,
            monitor_interval_minutes=self.settings.get("default_interval_minutes", 30),
            buzz_threshold_likes=self.default_threshold,
            buzz_threshold_ratio=3.0,
            posts_per_check=self.settings.get("default_max_posts", 50),
            auto_save_buzz=True,
            notify_on_buzz=True
        )

        return BuzzMonitor(config)

    async def run_once(self):
        """1回だけチェックを実行"""
        if not self.accounts:
            logger.error("No accounts to monitor")
            return

        logger.info("=" * 60)
        logger.info("🔍 Running single check...")
        logger.info(f"   Accounts: {len(self.accounts)}")
        logger.info("=" * 60)

        self.monitor = self.create_monitor()
        buzz_posts = await self.monitor.check_all_accounts()

        # ステータス更新
        save_status({
            "running": False,
            "last_check": datetime.now().isoformat(),
            "accounts_checked": len(self.accounts),
            "buzz_found": len(buzz_posts)
        })

        if buzz_posts:
            logger.info(f"🔥 Found {len(buzz_posts)} buzz posts!")
            for bp in sorted(buzz_posts, key=lambda x: x.likes, reverse=True)[:5]:
                logger.info(f"  @{bp.author_username}: ❤️ {bp.likes:,} | {bp.content[:40]}...")

            # Gmail通知 + スプシ出力
            logger.info("📧 Sending notifications...")
            buzz_dicts = [
                {
                    "author_username": bp.author_username,
                    "content": bp.content,
                    "likes": bp.likes,
                    "retweets": bp.retweets,
                    "views": bp.views,
                    "buzz_score": bp.buzz_score,
                    "reason": bp.reason,
                    "post_url": bp.post_url,
                    "category": get_account_category(bp.author_username) or "その他"
                }
                for bp in buzz_posts
            ]
            notify_result = self.notifier.notify(buzz_dicts)
            logger.info(f"📧 Notification result: {notify_result}")
        else:
            logger.info("No buzz posts found")

        return buzz_posts

    async def run_continuous(self):
        """継続的に監視を実行"""
        if not self.accounts:
            logger.error("No accounts to monitor")
            return

        self.running = True
        write_pid()

        # シグナルハンドラ設定
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        interval_minutes = self.settings.get("default_interval_minutes", 30)

        logger.info("=" * 60)
        logger.info("🚀 X Buzz Auto Monitor - Starting")
        logger.info("=" * 60)
        logger.info(f"  📡 監視間隔: {interval_minutes}分")
        logger.info(f"  🎯 バズ閾値: {self.default_threshold}")
        logger.info(f"  👤 監視対象: {len(self.accounts)}アカウント")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop")
        logger.info("")

        try:
            while self.running:
                # アカウントリストを再読み込み（動的に追加/削除可能）
                self.accounts = load_accounts()

                if not self.accounts:
                    logger.warning("No accounts to monitor, waiting...")
                    await asyncio.sleep(60)
                    continue

                # モニター実行
                self.monitor = self.create_monitor()
                buzz_posts = await self.monitor.check_all_accounts()

                # ステータス更新
                save_status({
                    "running": True,
                    "last_check": datetime.now().isoformat(),
                    "accounts_checked": len(self.accounts),
                    "buzz_found": len(buzz_posts),
                    "next_check": datetime.now().isoformat(),
                    "interval_minutes": interval_minutes
                })

                if buzz_posts:
                    logger.info(f"🔥 Found {len(buzz_posts)} buzz posts!")

                    # Gmail通知 + スプシ出力
                    logger.info("📧 Sending notifications...")
                    buzz_dicts = [
                        {
                            "author_username": bp.author_username,
                            "content": bp.content,
                            "likes": bp.likes,
                            "retweets": bp.retweets,
                            "views": bp.views,
                            "buzz_score": bp.buzz_score,
                            "reason": bp.reason,
                            "post_url": bp.post_url,
                            "category": get_account_category(bp.author_username) or "その他"
                        }
                        for bp in buzz_posts
                    ]
                    notify_result = self.notifier.notify(buzz_dicts)
                    logger.info(f"📧 Notification result: {notify_result}")

                # 次回チェックまで待機
                logger.info(f"⏰ Next check in {interval_minutes} minutes...")

                for _ in range(interval_minutes * 60):
                    if not self.running:
                        break
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Monitor cancelled")
        finally:
            self.running = False
            remove_pid()
            save_status({
                "running": False,
                "stopped_at": datetime.now().isoformat()
            })
            logger.info("✅ Auto Monitor stopped")

    def get_status(self) -> dict:
        """ステータスを取得"""
        status = load_status()
        status["pid_exists"] = PID_FILE.exists()
        status["is_running"] = is_running()
        status["accounts_count"] = len(self.accounts)
        status["accounts"] = self.accounts[:10]  # 最初の10件のみ
        return status


def daemonize():
    """デーモン化"""
    # 最初のfork
    if os.fork() > 0:
        sys.exit(0)

    # 新しいセッション
    os.setsid()

    # 2回目のfork
    if os.fork() > 0:
        sys.exit(0)

    # 作業ディレクトリ変更
    os.chdir(SCRIPT_DIR)

    # ファイルディスクリプタをリダイレクト
    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null', 'r') as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())

    log_file = LOGS_DIR / "auto_monitor_daemon.log"
    with open(log_file, 'a') as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Buzz Auto Monitor")
    parser.add_argument(
        "command",
        choices=["start", "run", "check", "status", "stop"],
        help="start: バックグラウンド起動, run: フォアグラウンド実行, check: 1回チェック, status: 状態確認, stop: 停止"
    )
    parser.add_argument("--daemon", "-d", action="store_true", help="デーモンとして起動")

    args = parser.parse_args()

    monitor = AutoMonitor()

    if args.command == "start":
        if is_running():
            print("❌ Auto Monitor is already running")
            status = monitor.get_status()
            print(f"   PID: {PID_FILE.read_text().strip() if PID_FILE.exists() else 'N/A'}")
            return

        print("🚀 Starting Auto Monitor in background...")

        # デーモン化
        daemonize()

        # メインループ実行
        await monitor.run_continuous()

    elif args.command == "run":
        if is_running():
            print("❌ Auto Monitor is already running")
            return

        await monitor.run_continuous()

    elif args.command == "check":
        await monitor.run_once()

    elif args.command == "status":
        status = monitor.get_status()

        print("=" * 50)
        print("📊 Auto Monitor Status")
        print("=" * 50)

        if status.get("is_running"):
            print(f"  ✅ Status: Running")
            if PID_FILE.exists():
                print(f"  📌 PID: {PID_FILE.read_text().strip()}")
        else:
            print(f"  ⏹️  Status: Stopped")

        print(f"  👤 Accounts: {status.get('accounts_count', 0)}")

        if status.get("last_check"):
            print(f"  ⏰ Last check: {status['last_check']}")

        if status.get("buzz_found") is not None:
            print(f"  🔥 Last buzz found: {status['buzz_found']}")

        print("")
        print("📋 Monitored accounts:")
        for acc in status.get("accounts", []):
            print(f"     @{acc}")

        if len(monitor.accounts) > 10:
            print(f"     ... and {len(monitor.accounts) - 10} more")

    elif args.command == "stop":
        if not is_running():
            print("❌ Auto Monitor is not running")
            return

        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"✅ Sent stop signal to PID {pid}")

            # 停止を待機
            import time
            for _ in range(10):
                if not is_running():
                    print("✅ Auto Monitor stopped")
                    remove_pid()
                    return
                time.sleep(1)

            print("⚠️  Process may still be running")
        except Exception as e:
            print(f"❌ Error stopping: {e}")
            remove_pid()


if __name__ == "__main__":
    asyncio.run(main())
