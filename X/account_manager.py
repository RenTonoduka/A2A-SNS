"""
X Account Manager - アカウントリスト管理・一括抽出
accounts.json からアカウントを読み込み、一括でバズ抽出
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field

# パス設定
SCRIPT_DIR = Path(__file__).parent
ACCOUNTS_FILE = SCRIPT_DIR / "accounts.json"
DATA_DIR = SCRIPT_DIR / "data"
LOGS_DIR = SCRIPT_DIR / "logs"

# ログ設定
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "account_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Account:
    """アカウント情報"""
    username: str
    category: str = "general"
    priority: str = "medium"  # high, medium, low
    notes: str = ""
    enabled: bool = True
    last_checked: Optional[str] = None
    total_posts_extracted: int = 0
    total_buzz_found: int = 0


class AccountManager:
    """
    アカウントリスト管理

    機能:
    1. accounts.json からアカウント読み込み
    2. カテゴリ・優先度でフィルタリング
    3. 一括抽出・監視
    4. 統計情報の管理
    """

    def __init__(self, accounts_file: Optional[Path] = None):
        self.accounts_file = accounts_file or ACCOUNTS_FILE
        self.accounts: List[Account] = []
        self.categories: Dict[str, Dict] = {}
        self.settings: Dict[str, Any] = {}
        self._load_accounts()

    def _load_accounts(self):
        """アカウントリストを読み込み"""
        if not self.accounts_file.exists():
            logger.warning(f"Accounts file not found: {self.accounts_file}")
            self._create_default_accounts_file()
            return

        try:
            data = json.loads(self.accounts_file.read_text())
            self.categories = data.get("categories", {})
            self.settings = data.get("settings", {})

            for acc_data in data.get("accounts", []):
                account = Account(
                    username=acc_data.get("username", ""),
                    category=acc_data.get("category", "general"),
                    priority=acc_data.get("priority", "medium"),
                    notes=acc_data.get("notes", ""),
                    enabled=acc_data.get("enabled", True),
                    last_checked=acc_data.get("last_checked"),
                    total_posts_extracted=acc_data.get("total_posts_extracted", 0),
                    total_buzz_found=acc_data.get("total_buzz_found", 0)
                )
                self.accounts.append(account)

            logger.info(f"Loaded {len(self.accounts)} accounts")

        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")

    def _create_default_accounts_file(self):
        """デフォルトのアカウントファイルを作成"""
        default_data = {
            "description": "監視・抽出対象のXアカウントリスト",
            "updated_at": datetime.now().isoformat(),
            "accounts": [],
            "categories": {
                "tech": {"description": "テクノロジー系", "buzz_threshold": 5000},
                "business": {"description": "ビジネス系", "buzz_threshold": 3000},
                "general": {"description": "一般", "buzz_threshold": 1000}
            },
            "settings": {
                "default_max_posts": 50,
                "default_interval_minutes": 30,
                "rate_limit_delay_seconds": 5
            }
        }
        self.accounts_file.write_text(json.dumps(default_data, ensure_ascii=False, indent=2))
        logger.info(f"Created default accounts file: {self.accounts_file}")

    def save_accounts(self):
        """アカウントリストを保存"""
        data = {
            "description": "監視・抽出対象のXアカウントリスト",
            "updated_at": datetime.now().isoformat(),
            "accounts": [asdict(acc) for acc in self.accounts],
            "categories": self.categories,
            "settings": self.settings
        }
        self.accounts_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"Saved {len(self.accounts)} accounts")

    # ==========================================
    # アカウント管理
    # ==========================================

    def add_account(
        self,
        username: str,
        category: str = "general",
        priority: str = "medium",
        notes: str = ""
    ) -> bool:
        """アカウントを追加"""
        username = username.lstrip("@")

        # 重複チェック
        if any(acc.username == username for acc in self.accounts):
            logger.warning(f"Account already exists: @{username}")
            return False

        account = Account(
            username=username,
            category=category,
            priority=priority,
            notes=notes,
            enabled=True
        )
        self.accounts.append(account)
        self.save_accounts()
        logger.info(f"Added account: @{username} ({category})")
        return True

    def remove_account(self, username: str) -> bool:
        """アカウントを削除"""
        username = username.lstrip("@")

        for i, acc in enumerate(self.accounts):
            if acc.username == username:
                del self.accounts[i]
                self.save_accounts()
                logger.info(f"Removed account: @{username}")
                return True

        logger.warning(f"Account not found: @{username}")
        return False

    def enable_account(self, username: str, enabled: bool = True) -> bool:
        """アカウントを有効/無効化"""
        username = username.lstrip("@")

        for acc in self.accounts:
            if acc.username == username:
                acc.enabled = enabled
                self.save_accounts()
                status = "enabled" if enabled else "disabled"
                logger.info(f"Account {status}: @{username}")
                return True

        return False

    def get_account(self, username: str) -> Optional[Account]:
        """アカウントを取得"""
        username = username.lstrip("@")
        for acc in self.accounts:
            if acc.username == username:
                return acc
        return None

    def update_account_stats(
        self,
        username: str,
        posts_extracted: int = 0,
        buzz_found: int = 0
    ):
        """アカウントの統計を更新"""
        username = username.lstrip("@")

        for acc in self.accounts:
            if acc.username == username:
                acc.last_checked = datetime.now().isoformat()
                acc.total_posts_extracted += posts_extracted
                acc.total_buzz_found += buzz_found
                self.save_accounts()
                return

    # ==========================================
    # フィルタリング
    # ==========================================

    def get_enabled_accounts(self) -> List[Account]:
        """有効なアカウントを取得"""
        return [acc for acc in self.accounts if acc.enabled]

    def get_accounts_by_category(self, category: str) -> List[Account]:
        """カテゴリでフィルタ"""
        return [acc for acc in self.accounts if acc.category == category and acc.enabled]

    def get_accounts_by_priority(self, priority: str) -> List[Account]:
        """優先度でフィルタ"""
        return [acc for acc in self.accounts if acc.priority == priority and acc.enabled]

    def get_high_priority_accounts(self) -> List[Account]:
        """高優先度アカウントを取得"""
        return self.get_accounts_by_priority("high")

    def get_usernames(self, accounts: Optional[List[Account]] = None) -> List[str]:
        """ユーザー名リストを取得"""
        accounts = accounts or self.get_enabled_accounts()
        return [acc.username for acc in accounts]

    # ==========================================
    # 一括抽出
    # ==========================================

    async def extract_all(
        self,
        max_posts: Optional[int] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        全アカウントから一括抽出

        Returns:
            {
                "total_accounts": N,
                "total_posts": N,
                "total_buzz": N,
                "results": {...}
            }
        """
        from monitor import BuzzMonitor, MonitorConfig

        # フィルタリング
        accounts = self.get_enabled_accounts()

        if category:
            accounts = [acc for acc in accounts if acc.category == category]
        if priority:
            accounts = [acc for acc in accounts if acc.priority == priority]

        if not accounts:
            return {"error": "No accounts to extract", "total_accounts": 0}

        logger.info(f"🚀 Starting bulk extraction for {len(accounts)} accounts")

        # 設定
        max_posts = max_posts or self.settings.get("default_max_posts", 50)
        delay = self.settings.get("rate_limit_delay_seconds", 5)

        # モニター設定
        config = MonitorConfig(
            target_accounts=self.get_usernames(accounts),
            posts_per_check=max_posts
        )

        monitor = BuzzMonitor(config)

        # 結果
        results = {
            "started_at": datetime.now().isoformat(),
            "total_accounts": len(accounts),
            "total_posts": 0,
            "total_buzz": 0,
            "accounts": {}
        }

        # 一括抽出
        for acc in accounts:
            try:
                logger.info(f"📥 Extracting @{acc.username}...")

                buzz_posts = await monitor.check_account(acc.username)

                # 統計更新
                posts_count = len(buzz_posts)
                self.update_account_stats(
                    acc.username,
                    posts_extracted=config.posts_per_check,
                    buzz_found=posts_count
                )

                results["accounts"][acc.username] = {
                    "category": acc.category,
                    "priority": acc.priority,
                    "buzz_found": posts_count,
                    "top_buzz": buzz_posts[0] if buzz_posts else None
                }
                results["total_buzz"] += posts_count

                # レート制限対策
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Error extracting @{acc.username}: {e}")
                results["accounts"][acc.username] = {"error": str(e)}

        results["completed_at"] = datetime.now().isoformat()
        logger.info(f"✅ Bulk extraction complete: {results['total_buzz']} buzz posts found")

        return results

    async def extract_by_category(self, category: str, max_posts: int = 50) -> Dict[str, Any]:
        """カテゴリ別に一括抽出"""
        return await self.extract_all(max_posts=max_posts, category=category)

    async def extract_high_priority(self, max_posts: int = 50) -> Dict[str, Any]:
        """高優先度アカウントのみ一括抽出"""
        return await self.extract_all(max_posts=max_posts, priority="high")

    # ==========================================
    # 表示・統計
    # ==========================================

    def list_accounts(self) -> List[Dict]:
        """アカウント一覧を取得"""
        return [
            {
                "username": acc.username,
                "category": acc.category,
                "priority": acc.priority,
                "enabled": acc.enabled,
                "notes": acc.notes,
                "last_checked": acc.last_checked,
                "total_posts": acc.total_posts_extracted,
                "total_buzz": acc.total_buzz_found
            }
            for acc in self.accounts
        ]

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        enabled = self.get_enabled_accounts()

        by_category = {}
        for acc in enabled:
            cat = acc.category
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] += 1

        by_priority = {}
        for acc in enabled:
            pri = acc.priority
            if pri not in by_priority:
                by_priority[pri] = 0
            by_priority[pri] += 1

        return {
            "total_accounts": len(self.accounts),
            "enabled_accounts": len(enabled),
            "by_category": by_category,
            "by_priority": by_priority,
            "total_posts_extracted": sum(acc.total_posts_extracted for acc in self.accounts),
            "total_buzz_found": sum(acc.total_buzz_found for acc in self.accounts)
        }


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Account Manager")
    parser.add_argument("command", choices=[
        "list", "add", "remove", "enable", "disable",
        "extract-all", "extract-category", "extract-priority",
        "stats", "export"
    ], help="コマンド")
    parser.add_argument("--username", "-u", help="ユーザー名")
    parser.add_argument("--category", "-c", help="カテゴリ")
    parser.add_argument("--priority", "-p", choices=["high", "medium", "low"], help="優先度")
    parser.add_argument("--notes", "-n", default="", help="メモ")
    parser.add_argument("--max", type=int, default=50, help="最大取得数")

    args = parser.parse_args()

    manager = AccountManager()

    if args.command == "list":
        accounts = manager.list_accounts()
        print(f"📋 アカウント一覧 ({len(accounts)}件):\n")

        for acc in accounts:
            status = "✅" if acc["enabled"] else "❌"
            pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(acc["priority"], "⚪")
            print(f"  {status} @{acc['username']} [{acc['category']}] {pri_icon}")
            if acc["notes"]:
                print(f"      {acc['notes']}")
            if acc["last_checked"]:
                print(f"      最終チェック: {acc['last_checked'][:19]}")
                print(f"      バズ検出: {acc['total_buzz']}件")
            print()

    elif args.command == "add":
        if not args.username:
            print("❌ --username が必要です")
            return

        if manager.add_account(
            args.username,
            category=args.category or "general",
            priority=args.priority or "medium",
            notes=args.notes
        ):
            print(f"✅ 追加しました: @{args.username.lstrip('@')}")
        else:
            print(f"❌ 既に存在します: @{args.username.lstrip('@')}")

    elif args.command == "remove":
        if not args.username:
            print("❌ --username が必要です")
            return

        if manager.remove_account(args.username):
            print(f"✅ 削除しました: @{args.username.lstrip('@')}")
        else:
            print(f"❌ 見つかりません: @{args.username.lstrip('@')}")

    elif args.command == "enable":
        if not args.username:
            print("❌ --username が必要です")
            return
        manager.enable_account(args.username, True)
        print(f"✅ 有効化しました: @{args.username.lstrip('@')}")

    elif args.command == "disable":
        if not args.username:
            print("❌ --username が必要です")
            return
        manager.enable_account(args.username, False)
        print(f"✅ 無効化しました: @{args.username.lstrip('@')}")

    elif args.command == "extract-all":
        print("🚀 全アカウントから一括抽出中...")
        results = await manager.extract_all(max_posts=args.max)
        print(f"\n✅ 完了!")
        print(f"  対象アカウント: {results['total_accounts']}件")
        print(f"  バズ検出: {results['total_buzz']}件")

    elif args.command == "extract-category":
        if not args.category:
            print("❌ --category が必要です")
            print(f"利用可能: {list(manager.categories.keys())}")
            return

        print(f"🚀 カテゴリ '{args.category}' から一括抽出中...")
        results = await manager.extract_by_category(args.category, max_posts=args.max)
        print(f"\n✅ 完了! バズ検出: {results['total_buzz']}件")

    elif args.command == "extract-priority":
        priority = args.priority or "high"
        print(f"🚀 優先度 '{priority}' から一括抽出中...")
        results = await manager.extract_all(max_posts=args.max, priority=priority)
        print(f"\n✅ 完了! バズ検出: {results['total_buzz']}件")

    elif args.command == "stats":
        stats = manager.get_stats()
        print("📊 統計情報:\n")
        print(f"  総アカウント数: {stats['total_accounts']}")
        print(f"  有効アカウント: {stats['enabled_accounts']}")
        print(f"\n  カテゴリ別:")
        for cat, count in stats["by_category"].items():
            print(f"    {cat}: {count}件")
        print(f"\n  優先度別:")
        for pri, count in stats["by_priority"].items():
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(pri, "⚪")
            print(f"    {icon} {pri}: {count}件")
        print(f"\n  累計抽出ポスト: {stats['total_posts_extracted']}")
        print(f"  累計バズ検出: {stats['total_buzz_found']}")

    elif args.command == "export":
        accounts = manager.list_accounts()
        print(json.dumps(accounts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
