"""
YouTube Auto Scheduler - A2A版
Master Coordinator経由で全Phase（0-4）を自動実行
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))

# ログ設定
log_dir = SCRIPT_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# スケジューラ
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


@dataclass
class SchedulerConfig:
    """スケジューラ設定"""
    # Master Coordinator
    master_coordinator_url: str = "http://localhost:8099"

    # 定期実行設定
    daily_run_hour: int = 9
    daily_run_minute: int = 0
    weekly_run_day: str = "mon"

    # 監視設定
    monitor_interval_minutes: int = 30

    # 自動実行設定
    max_daily_scripts: int = 3

    # 通知設定
    notify_on_buzz: bool = True
    notify_on_complete: bool = True


class A2AScheduler:
    """
    A2A版スケジューラ

    全ての処理をMaster Coordinator経由で実行

    フロー:
    1. 定期トリガー → Master Coordinator
    2. Master Coordinator → 各Phase Agent (A2A)
    3. 結果をログ・通知
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self.scheduler = AsyncIOScheduler() if SCHEDULER_AVAILABLE else None
        self.running = False
        self.daily_script_count = 0
        self.last_reset_date = datetime.now().date()

        # 状態ファイル
        self.state_file = SCRIPT_DIR / "logs" / "scheduler_state.json"
        self._load_state()

    def _load_state(self):
        """状態を読み込み"""
        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                self.daily_script_count = state.get("daily_script_count", 0)
                last_reset = state.get("last_reset_date")
                if last_reset:
                    self.last_reset_date = datetime.fromisoformat(last_reset).date()
            except:
                pass

    def _save_state(self):
        """状態を保存"""
        state = {
            "daily_script_count": self.daily_script_count,
            "last_reset_date": self.last_reset_date.isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    def _reset_daily_count(self):
        """日次カウントをリセット"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_script_count = 0
            self.last_reset_date = today
            self._save_state()
            logger.info("Daily script count reset")

    # ==========================================
    # A2A呼び出し
    # ==========================================

    def _call_master_coordinator(self, endpoint: str, method: str = "POST", timeout: int = 600) -> Dict:
        """
        Master CoordinatorをHTTPで呼び出し

        Args:
            endpoint: エンドポイント (例: /trigger/buzz-check)
            method: HTTPメソッド
            timeout: タイムアウト秒数

        Returns:
            レスポンスJSON
        """
        url = f"{self.config.master_coordinator_url}{endpoint}"

        try:
            req = urllib.request.Request(url, method=method)
            req.add_header('Content-Type', 'application/json')

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            return {"error": str(e), "status": "failed"}
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            return {"error": str(e), "status": "failed"}
        except Exception as e:
            logger.error(f"Request Error: {e}")
            return {"error": str(e), "status": "failed"}

    def _send_a2a_task(self, message: str, timeout: int = 600) -> Dict:
        """
        A2Aタスクを送信

        Args:
            message: 送信メッセージ
            timeout: タイムアウト秒数

        Returns:
            タスク結果
        """
        url = f"{self.config.master_coordinator_url}/a2a/tasks/send"

        payload = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}]
            }
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header('Content-Type', 'application/json')

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result

        except Exception as e:
            logger.error(f"A2A Task Error: {e}")
            return {"error": str(e), "status": "failed"}

    # ==========================================
    # トリガー関数（Master Coordinator経由）
    # ==========================================

    async def trigger_buzz_check(self) -> Dict:
        """バズチェックをトリガー（A2A経由）"""
        logger.info("🔍 [A2A] Triggering buzz check via Master Coordinator...")

        result = self._call_master_coordinator("/trigger/buzz-check", timeout=300)

        if "error" not in result:
            logger.info("✅ Buzz check completed")
            # 結果からバズ検出があったか確認
            result_text = json.dumps(result, ensure_ascii=False)
            if "バズ" in result_text and "検出" in result_text:
                logger.info("🔥 Buzz videos detected!")
        else:
            logger.error(f"❌ Buzz check failed: {result.get('error')}")

        return result

    async def trigger_full_pipeline(self, theme: Optional[str] = None) -> Dict:
        """フルパイプラインをトリガー（A2A経由）"""
        self._reset_daily_count()

        if self.daily_script_count >= self.config.max_daily_scripts:
            logger.warning(f"⚠️ Daily limit reached ({self.config.max_daily_scripts})")
            return {"error": "daily_limit_reached", "count": self.daily_script_count}

        logger.info("🎬 [A2A] Triggering full pipeline via Master Coordinator...")

        if theme:
            # テーマ指定の場合はA2Aタスクで送信
            result = self._send_a2a_task(f"「{theme}」で台本を作成してください", timeout=600)
        else:
            # テーマなしの場合は直接トリガー
            result = self._call_master_coordinator("/trigger/full-pipeline", timeout=600)

        if "error" not in result:
            self.daily_script_count += 1
            self._save_state()
            logger.info(f"✅ Pipeline completed! (Daily count: {self.daily_script_count})")

            # スコア抽出
            result_text = json.dumps(result, ensure_ascii=False)
            import re
            score_match = re.search(r'"final_score"\s*:\s*(\d+)', result_text)
            if score_match:
                logger.info(f"📊 Final score: {score_match.group(1)}")
        else:
            logger.error(f"❌ Pipeline failed: {result.get('error')}")

        return result

    async def get_system_status(self) -> Dict:
        """システム状態を取得"""
        logger.info("📊 [A2A] Getting system status...")

        result = self._call_master_coordinator("/status", method="GET", timeout=30)

        if "error" not in result:
            # エージェント状態をログ
            agents = result.get("agents", {})
            online = sum(1 for v in agents.values() if v)
            total = len(agents)
            logger.info(f"📡 Agents online: {online}/{total}")

        return result

    # ==========================================
    # 定期実行ジョブ
    # ==========================================

    async def job_monitor_buzz(self):
        """定期バズ監視ジョブ（A2A版）"""
        logger.info("⏰ [Scheduled] Buzz monitoring job started")

        # Master Coordinator経由でバズチェック
        result = await self.trigger_buzz_check()

        # バズが見つかったら自動で台本生成
        if "error" not in result:
            result_text = json.dumps(result, ensure_ascii=False)
            if "バズ" in result_text or "buzz" in result_text.lower():
                if self.daily_script_count < self.config.max_daily_scripts:
                    logger.info("🔥 Buzz detected! Auto-triggering pipeline...")
                    await self.trigger_full_pipeline()

        logger.info("⏰ [Scheduled] Buzz monitoring job completed")

    async def job_daily_pipeline(self):
        """毎日の定時パイプライン実行（A2A版）"""
        logger.info("⏰ [Scheduled] Daily pipeline job started")

        # 日次カウントリセット
        self._reset_daily_count()

        # Master Coordinator経由でフルパイプライン
        await self.trigger_full_pipeline()

        logger.info("⏰ [Scheduled] Daily pipeline job completed")

    async def job_weekly_analysis(self):
        """週次分析ジョブ（A2A版）"""
        logger.info("⏰ [Scheduled] Weekly analysis job started")

        # A2Aタスクで週次レポート要求
        result = self._send_a2a_task("週次トレンドレポートを生成してください", timeout=300)

        if "error" not in result:
            logger.info("✅ Weekly report generated")
        else:
            logger.error(f"❌ Weekly report failed: {result.get('error')}")

        logger.info("⏰ [Scheduled] Weekly analysis job completed")

    # ==========================================
    # スケジューラ制御
    # ==========================================

    def setup_schedules(self):
        """スケジュールを設定"""
        if not self.scheduler:
            logger.error("Scheduler not available. Install: pip install apscheduler")
            return

        # バズ監視（30分ごと）
        self.scheduler.add_job(
            self.job_monitor_buzz,
            IntervalTrigger(minutes=self.config.monitor_interval_minutes),
            id="buzz_monitor",
            name="Buzz Video Monitor (A2A)",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Buzz monitor every {self.config.monitor_interval_minutes} min")

        # 毎日定時実行
        self.scheduler.add_job(
            self.job_daily_pipeline,
            CronTrigger(
                hour=self.config.daily_run_hour,
                minute=self.config.daily_run_minute
            ),
            id="daily_pipeline",
            name="Daily Pipeline (A2A)",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Daily pipeline at {self.config.daily_run_hour:02d}:{self.config.daily_run_minute:02d}")

        # 週次分析（毎週月曜）
        self.scheduler.add_job(
            self.job_weekly_analysis,
            CronTrigger(
                day_of_week=self.config.weekly_run_day,
                hour=10,
                minute=0
            ),
            id="weekly_analysis",
            name="Weekly Analysis (A2A)",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Weekly analysis on {self.config.weekly_run_day}")

    async def start(self, run_immediately: bool = True):
        """スケジューラを開始"""
        logger.info("🚀 Starting A2A Scheduler...")

        self.running = True

        # Master Coordinator接続確認
        logger.info(f"🔗 Connecting to Master Coordinator: {self.config.master_coordinator_url}")
        status = await self.get_system_status()
        if "error" in status:
            logger.warning(f"⚠️ Master Coordinator not responding. Will retry on jobs.")
        else:
            logger.info("✅ Master Coordinator connected")

        # スケジュール設定
        if self.scheduler:
            self.setup_schedules()
            self.scheduler.start()
            logger.info("✅ Scheduler started")

        # 起動時に即座にバズチェック
        if run_immediately:
            logger.info("🔥 Running initial buzz check...")
            await self.job_monitor_buzz()

        # メインループ
        try:
            while self.running:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def stop(self):
        """スケジューラを停止"""
        logger.info("🛑 Stopping A2A Scheduler...")
        self.running = False

        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()

        self._save_state()
        logger.info("✅ Scheduler stopped")

    def get_status(self) -> Dict:
        """現在のステータスを取得"""
        return {
            "running": self.running,
            "daily_script_count": self.daily_script_count,
            "max_daily_scripts": self.config.max_daily_scripts,
            "last_reset_date": self.last_reset_date.isoformat(),
            "master_coordinator_url": self.config.master_coordinator_url,
            "config": asdict(self.config),
            "next_jobs": self._get_next_jobs() if self.scheduler else []
        }

    def _get_next_jobs(self) -> List[Dict]:
        """次のジョブ実行予定を取得"""
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                })
        return jobs


# ==========================================
# CLI
# ==========================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube A2A Scheduler")
    parser.add_argument("command", choices=["start", "status", "run-once", "buzz-check", "pipeline"],
                       help="start: スケジューラ開始, status: 状態確認, run-once: 1回実行, buzz-check: バズチェック, pipeline: フルパイプライン")
    parser.add_argument("--no-immediate", action="store_true",
                       help="起動時の即座実行をスキップ")
    parser.add_argument("--interval", type=int, default=30,
                       help="監視間隔（分）")
    parser.add_argument("--hour", type=int, default=9,
                       help="毎日実行時刻（時）")
    parser.add_argument("--master-url", type=str, default="http://localhost:8099",
                       help="Master Coordinator URL")
    parser.add_argument("--theme", type=str,
                       help="台本生成テーマ（pipeline時）")

    args = parser.parse_args()

    config = SchedulerConfig(
        master_coordinator_url=args.master_url,
        monitor_interval_minutes=args.interval,
        daily_run_hour=args.hour
    )

    scheduler = A2AScheduler(config)

    if args.command == "start":
        print("=" * 60)
        print("🤖 YouTube A2A Scheduler")
        print("=" * 60)
        print(f"  🔗 Master Coordinator: {config.master_coordinator_url}")
        print(f"  📡 Buzz monitor: every {config.monitor_interval_minutes} min")
        print(f"  📅 Daily run: {config.daily_run_hour:02d}:00")
        print(f"  📝 Max daily scripts: {config.max_daily_scripts}")
        print("=" * 60)
        print("All tasks execute via A2A → Master Coordinator")
        print("Press Ctrl+C to stop")
        print("")

        await scheduler.start(run_immediately=not args.no_immediate)

    elif args.command == "status":
        # ローカル状態
        local_status = scheduler.get_status()
        print("=== Local Scheduler Status ===")
        print(json.dumps(local_status, ensure_ascii=False, indent=2))

        # Master Coordinator状態
        print("\n=== Master Coordinator Status ===")
        mc_status = await scheduler.get_system_status()
        print(json.dumps(mc_status, ensure_ascii=False, indent=2))

    elif args.command == "run-once":
        print("🔥 Running single pipeline execution via A2A...")
        await scheduler.job_daily_pipeline()

    elif args.command == "buzz-check":
        print("🔍 Triggering buzz check via A2A...")
        result = await scheduler.trigger_buzz_check()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "pipeline":
        print("🎬 Triggering full pipeline via A2A...")
        result = await scheduler.trigger_full_pipeline(theme=args.theme)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
