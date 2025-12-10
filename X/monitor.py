"""
X Buzz Monitor - バズポスト監視システム
特定アカウントを定期監視し、バズポストを自動検出
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from config import DATA_DIR, LOGS_DIR

# ログ設定
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# スケジューラ（APScheduler）
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


@dataclass
class MonitorConfig:
    """モニタリング設定"""
    # 監視対象アカウント
    target_accounts: List[str] = field(default_factory=list)

    # 監視間隔
    monitor_interval_minutes: int = 30      # 監視間隔（分）

    # バズ判定基準
    buzz_threshold_likes: int = 1000        # バズ判定: いいね数
    buzz_threshold_ratio: float = 3.0       # バズ判定: 平均の何倍か
    buzz_min_engagement: int = 100          # 最小エンゲージメント

    # 抽出設定
    posts_per_check: int = 20               # 1回のチェックで取得する件数
    include_replies: bool = False
    include_retweets: bool = False

    # 通知設定
    notify_on_buzz: bool = True             # バズ検出時に通知
    notification_webhook: Optional[str] = None  # Webhook URL (Discord/Slack等)

    # 自動処理
    auto_save_buzz: bool = True             # バズポストを自動保存
    max_buzz_per_day: int = 50              # 1日の最大バズ保存数


@dataclass
class BuzzPost:
    """バズポスト情報"""
    post_id: str
    author_username: str
    author_name: str
    content: str
    timestamp: str
    likes: int
    retweets: int
    replies: int
    views: int
    post_url: str
    buzz_score: float               # バズスコア（平均の何倍か）
    detected_at: str                # 検出日時
    reason: str                     # バズ判定理由


class BuzzMonitor:
    """
    バズポスト監視システム

    機能:
    1. 定期監視: 指定アカウントを定期的にチェック
    2. バズ検出: エンゲージメントが閾値を超えたポストを検出
    3. 自動保存: バズポストを自動でファイルに保存
    4. 通知: バズ検出時にWebhookで通知
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.scheduler = AsyncIOScheduler() if SCHEDULER_AVAILABLE else None
        self.running = False

        # 統計情報
        self.daily_buzz_count = 0
        self.last_reset_date = datetime.now().date()
        self.account_stats: Dict[str, Dict] = {}  # アカウントごとの統計

        # ファイルパス
        self.state_file = LOGS_DIR / "monitor_state.json"
        self.buzz_dir = DATA_DIR / "buzz"
        self.buzz_dir.mkdir(parents=True, exist_ok=True)

        self._load_state()

    def _load_state(self):
        """状態を読み込み"""
        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                self.daily_buzz_count = state.get("daily_buzz_count", 0)
                last_reset = state.get("last_reset_date")
                if last_reset:
                    self.last_reset_date = datetime.fromisoformat(last_reset).date()
                self.account_stats = state.get("account_stats", {})
            except Exception as e:
                logger.warning(f"State load error: {e}")

    def _save_state(self):
        """状態を保存"""
        state = {
            "daily_buzz_count": self.daily_buzz_count,
            "last_reset_date": self.last_reset_date.isoformat(),
            "account_stats": self.account_stats,
            "last_updated": datetime.now().isoformat()
        }
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    def _reset_daily_count(self):
        """日次カウントをリセット"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_buzz_count = 0
            self.last_reset_date = today
            self._save_state()
            logger.info("Daily buzz count reset")

    # ==========================================
    # アカウント管理
    # ==========================================

    def add_account(self, username: str) -> bool:
        """監視対象アカウントを追加"""
        username = username.lstrip("@")
        if username not in self.config.target_accounts:
            self.config.target_accounts.append(username)
            self.account_stats[username] = {
                "total_posts_checked": 0,
                "buzz_posts_found": 0,
                "avg_likes": 0,
                "avg_retweets": 0,
                "last_checked": None
            }
            logger.info(f"Added monitoring target: @{username}")
            return True
        return False

    def remove_account(self, username: str) -> bool:
        """監視対象アカウントを削除"""
        username = username.lstrip("@")
        if username in self.config.target_accounts:
            self.config.target_accounts.remove(username)
            self.account_stats.pop(username, None)
            logger.info(f"Removed monitoring target: @{username}")
            return True
        return False

    def list_accounts(self) -> List[Dict]:
        """監視対象アカウント一覧"""
        return [
            {
                "username": username,
                "stats": self.account_stats.get(username, {})
            }
            for username in self.config.target_accounts
        ]

    # ==========================================
    # ポスト抽出・バズ検出
    # ==========================================

    async def extract_posts(self, username: str) -> List[Dict]:
        """ポストを抽出"""
        from post_extractor import PostExtractor
        from config import ExtractorConfig, BrowserConfig

        extractor_config = ExtractorConfig(
            max_posts_per_account=self.config.posts_per_check,
            include_replies=self.config.include_replies,
            include_retweets=self.config.include_retweets
        )

        browser_config = BrowserConfig(headless=True)

        try:
            extractor = PostExtractor(extractor_config, browser_config)
            posts = await extractor.extract_from_account(username)
            return [asdict(post) for post in posts]
        except Exception as e:
            logger.error(f"Extract error for @{username}: {e}")
            return []

    def calculate_buzz_score(self, post: Dict, avg_likes: float, avg_retweets: float) -> float:
        """バズスコアを計算（平均の何倍か）"""
        if avg_likes == 0:
            avg_likes = 1
        if avg_retweets == 0:
            avg_retweets = 1

        likes_ratio = post.get("likes", 0) / avg_likes
        rt_ratio = post.get("retweets", 0) / avg_retweets

        # いいね比率を重視（0.7:0.3）
        return likes_ratio * 0.7 + rt_ratio * 0.3

    def is_buzz_post(self, post: Dict, buzz_score: float) -> tuple[bool, str]:
        """バズポストかどうかを判定"""
        reasons = []

        likes = post.get("likes", 0)

        # 絶対値基準
        if likes >= self.config.buzz_threshold_likes:
            reasons.append(f"いいね{likes:,}件 (閾値: {self.config.buzz_threshold_likes:,})")

        # 相対値基準（平均の何倍か）
        if buzz_score >= self.config.buzz_threshold_ratio:
            reasons.append(f"バズスコア{buzz_score:.1f}x (閾値: {self.config.buzz_threshold_ratio}x)")

        is_buzz = len(reasons) > 0
        reason = " / ".join(reasons) if reasons else ""

        return is_buzz, reason

    async def check_account(self, username: str) -> List[BuzzPost]:
        """特定アカウントをチェックしてバズポストを検出"""
        logger.info(f"🔍 Checking @{username}...")

        username = username.lstrip("@")
        buzz_posts = []

        # ポスト抽出
        posts = await self.extract_posts(username)

        if not posts:
            logger.warning(f"No posts found for @{username}")
            return []

        # 平均値計算
        total_likes = sum(p.get("likes", 0) for p in posts)
        total_retweets = sum(p.get("retweets", 0) for p in posts)
        avg_likes = total_likes / len(posts) if posts else 0
        avg_retweets = total_retweets / len(posts) if posts else 0

        # 統計更新
        if username not in self.account_stats:
            self.account_stats[username] = {}

        self.account_stats[username].update({
            "total_posts_checked": self.account_stats.get(username, {}).get("total_posts_checked", 0) + len(posts),
            "avg_likes": avg_likes,
            "avg_retweets": avg_retweets,
            "last_checked": datetime.now().isoformat()
        })

        # バズ判定
        for post in posts:
            buzz_score = self.calculate_buzz_score(post, avg_likes, avg_retweets)
            is_buzz, reason = self.is_buzz_post(post, buzz_score)

            if is_buzz:
                buzz_post = BuzzPost(
                    post_id=post.get("post_id", ""),
                    author_username=post.get("author_username", username),
                    author_name=post.get("author_name", ""),
                    content=post.get("content", "")[:280],
                    timestamp=post.get("timestamp", ""),
                    likes=post.get("likes", 0),
                    retweets=post.get("retweets", 0),
                    replies=post.get("replies", 0),
                    views=post.get("views", 0),
                    post_url=post.get("post_url", ""),
                    buzz_score=buzz_score,
                    detected_at=datetime.now().isoformat(),
                    reason=reason
                )
                buzz_posts.append(buzz_post)

        if buzz_posts:
            logger.info(f"🔥 Found {len(buzz_posts)} buzz posts from @{username}")
            self.account_stats[username]["buzz_posts_found"] = (
                self.account_stats.get(username, {}).get("buzz_posts_found", 0) + len(buzz_posts)
            )

        self._save_state()
        return buzz_posts

    async def check_all_accounts(self) -> List[BuzzPost]:
        """全監視対象アカウントをチェック"""
        logger.info("🔍 Checking all monitored accounts...")

        all_buzz = []

        for username in self.config.target_accounts:
            try:
                buzz_posts = await self.check_account(username)
                all_buzz.extend(buzz_posts)

                # レート制限対策
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error checking @{username}: {e}")

        if all_buzz:
            logger.info(f"🔥 Total buzz posts found: {len(all_buzz)}")

            # 自動保存
            if self.config.auto_save_buzz:
                await self.save_buzz_posts(all_buzz)

            # 通知
            if self.config.notify_on_buzz:
                await self.notify_buzz(all_buzz)
        else:
            logger.info("No buzz posts found")

        return all_buzz

    # ==========================================
    # 保存・通知
    # ==========================================

    async def save_buzz_posts(self, buzz_posts: List[BuzzPost]):
        """バズポストを保存"""
        self._reset_daily_count()

        if self.daily_buzz_count >= self.config.max_buzz_per_day:
            logger.warning(f"Daily buzz limit reached ({self.config.max_buzz_per_day})")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.buzz_dir / f"buzz_{timestamp}.json"

        data = {
            "detected_at": datetime.now().isoformat(),
            "count": len(buzz_posts),
            "posts": [asdict(bp) for bp in buzz_posts]
        }

        filename.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"📁 Saved buzz posts to: {filename}")

        self.daily_buzz_count += len(buzz_posts)
        self._save_state()

    async def notify_buzz(self, buzz_posts: List[BuzzPost]):
        """バズ検出通知を送信"""
        if not self.config.notification_webhook:
            return

        # 上位3件のみ通知
        top_buzz = sorted(buzz_posts, key=lambda x: x.likes, reverse=True)[:3]

        message_lines = ["🔥 **バズポスト検出!**\n"]

        for bp in top_buzz:
            message_lines.append(
                f"**@{bp.author_username}** - ❤️ {bp.likes:,} | 🔄 {bp.retweets:,}\n"
                f"```{bp.content[:100]}...```\n"
                f"🔗 {bp.post_url}\n"
            )

        message = "\n".join(message_lines)

        try:
            import urllib.request

            payload = {"content": message}
            data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                self.config.notification_webhook,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200 or response.status == 204:
                    logger.info("📣 Notification sent")
        except Exception as e:
            logger.error(f"Notification error: {e}")

    # ==========================================
    # 定期実行ジョブ
    # ==========================================

    async def job_monitor(self):
        """定期監視ジョブ"""
        logger.info("⏰ [Scheduled] Monitor job started")
        await self.check_all_accounts()
        logger.info("⏰ [Scheduled] Monitor job completed")

    def setup_schedules(self):
        """スケジュールを設定"""
        if not self.scheduler:
            logger.error("Scheduler not available. Install: pip install apscheduler")
            return

        self.scheduler.add_job(
            self.job_monitor,
            IntervalTrigger(minutes=self.config.monitor_interval_minutes),
            id="buzz_monitor",
            name="Buzz Post Monitor",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Monitor every {self.config.monitor_interval_minutes} minutes")

    async def start(self, run_immediately: bool = True):
        """モニタリングを開始"""
        if not self.config.target_accounts:
            logger.warning("No target accounts configured. Add accounts first.")
            return

        logger.info("🚀 Starting Buzz Monitor...")
        self.running = True

        # スケジュール設定
        if self.scheduler:
            self.setup_schedules()
            self.scheduler.start()
            logger.info("✅ Scheduler started")

        # 即座にチェック
        if run_immediately:
            logger.info("🔥 Running initial check...")
            await self.job_monitor()

        # メインループ
        try:
            while self.running:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def stop(self):
        """モニタリングを停止"""
        logger.info("🛑 Stopping Buzz Monitor...")
        self.running = False

        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()

        self._save_state()
        logger.info("✅ Monitor stopped")

    def get_status(self) -> Dict:
        """現在のステータスを取得"""
        return {
            "running": self.running,
            "target_accounts": self.config.target_accounts,
            "account_count": len(self.config.target_accounts),
            "daily_buzz_count": self.daily_buzz_count,
            "max_buzz_per_day": self.config.max_buzz_per_day,
            "monitor_interval_minutes": self.config.monitor_interval_minutes,
            "buzz_threshold_likes": self.config.buzz_threshold_likes,
            "buzz_threshold_ratio": self.config.buzz_threshold_ratio,
            "account_stats": self.account_stats,
            "last_reset_date": self.last_reset_date.isoformat()
        }

    def get_recent_buzz(self, limit: int = 10) -> List[Dict]:
        """最近のバズポストを取得"""
        buzz_files = sorted(self.buzz_dir.glob("buzz_*.json"), reverse=True)[:limit]

        all_buzz = []
        for f in buzz_files:
            try:
                data = json.loads(f.read_text())
                all_buzz.extend(data.get("posts", []))
            except:
                pass

        # いいね数でソート
        all_buzz.sort(key=lambda x: x.get("likes", 0), reverse=True)
        return all_buzz[:limit]


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="X Buzz Monitor")
    parser.add_argument("command", choices=["start", "status", "check", "add", "remove", "list", "recent"],
                       help="start: 監視開始, status: 状態確認, check: 1回チェック, add: アカウント追加, remove: 削除, list: 一覧, recent: 最近のバズ")
    parser.add_argument("--account", "-a", type=str, help="対象アカウント (@username)")
    parser.add_argument("--accounts", nargs="+", help="複数アカウント")
    parser.add_argument("--interval", type=int, default=30, help="監視間隔（分）")
    parser.add_argument("--threshold", type=int, default=1000, help="バズ判定いいね閾値")
    parser.add_argument("--ratio", type=float, default=3.0, help="バズ判定倍率閾値")
    parser.add_argument("--no-immediate", action="store_true", help="即座実行をスキップ")
    parser.add_argument("--limit", type=int, default=10, help="表示件数")

    args = parser.parse_args()

    # 設定
    config = MonitorConfig(
        target_accounts=args.accounts or [],
        monitor_interval_minutes=args.interval,
        buzz_threshold_likes=args.threshold,
        buzz_threshold_ratio=args.ratio
    )

    monitor = BuzzMonitor(config)

    if args.command == "start":
        if args.account:
            monitor.add_account(args.account)
        if args.accounts:
            for acc in args.accounts:
                monitor.add_account(acc)

        if not monitor.config.target_accounts:
            print("❌ 監視対象アカウントを指定してください")
            print("例: python monitor.py start --account @elonmusk")
            return

        print("=" * 60)
        print("🔥 X Buzz Monitor")
        print("=" * 60)
        print(f"  📡 監視間隔: {config.monitor_interval_minutes}分")
        print(f"  🎯 バズ閾値: いいね >= {config.buzz_threshold_likes:,}")
        print(f"  📊 バズ倍率: >= {config.buzz_threshold_ratio}x")
        print(f"  👤 監視対象: {', '.join('@' + a for a in monitor.config.target_accounts)}")
        print("=" * 60)
        print("Press Ctrl+C to stop")
        print("")

        await monitor.start(run_immediately=not args.no_immediate)

    elif args.command == "status":
        status = monitor.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif args.command == "check":
        if args.account:
            monitor.add_account(args.account)
        if args.accounts:
            for acc in args.accounts:
                monitor.add_account(acc)

        if not monitor.config.target_accounts:
            print("❌ チェック対象アカウントを指定してください")
            return

        print(f"🔍 Checking {len(monitor.config.target_accounts)} accounts...")
        buzz = await monitor.check_all_accounts()

        if buzz:
            print(f"\n🔥 Found {len(buzz)} buzz posts:")
            for bp in sorted(buzz, key=lambda x: x.likes, reverse=True)[:5]:
                print(f"  @{bp.author_username}: ❤️ {bp.likes:,} | {bp.content[:50]}...")
        else:
            print("❌ No buzz posts found")

    elif args.command == "add":
        if args.account:
            if monitor.add_account(args.account):
                print(f"✅ Added: @{args.account.lstrip('@')}")
            else:
                print(f"Already exists: @{args.account.lstrip('@')}")

    elif args.command == "remove":
        if args.account:
            if monitor.remove_account(args.account):
                print(f"✅ Removed: @{args.account.lstrip('@')}")
            else:
                print(f"Not found: @{args.account.lstrip('@')}")

    elif args.command == "list":
        accounts = monitor.list_accounts()
        if accounts:
            print("📋 監視対象アカウント:")
            for acc in accounts:
                stats = acc["stats"]
                print(f"  @{acc['username']}")
                if stats.get("last_checked"):
                    print(f"    最終チェック: {stats['last_checked']}")
                    print(f"    バズ検出数: {stats.get('buzz_posts_found', 0)}")
        else:
            print("監視対象アカウントはありません")

    elif args.command == "recent":
        buzz = monitor.get_recent_buzz(limit=args.limit)
        if buzz:
            print(f"🔥 最近のバズポスト (Top {args.limit}):")
            for i, bp in enumerate(buzz, 1):
                print(f"\n{i}. @{bp['author_username']} - ❤️ {bp['likes']:,} | 🔄 {bp['retweets']:,}")
                print(f"   {bp['content'][:80]}...")
                print(f"   🔗 {bp['post_url']}")
        else:
            print("バズポストはまだ検出されていません")


if __name__ == "__main__":
    asyncio.run(main())
