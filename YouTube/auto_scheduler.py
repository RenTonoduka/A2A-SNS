"""
YouTube Auto Scheduler - 自動実行・定期実行・監視トリガー
Phase 0エージェントと連携し、バズ動画検出→台本生成を自動化
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import threading
import time

# パス設定
SCRIPT_DIR = Path(__file__).parent
SNS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SNS_DIR))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / "logs" / "scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# スケジューラ（APScheduler）
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
    # 定期実行設定
    daily_run_hour: int = 9          # 毎日実行時刻（時）
    daily_run_minute: int = 0        # 毎日実行時刻（分）
    weekly_run_day: str = "mon"      # 週次実行曜日

    # 監視設定
    monitor_interval_minutes: int = 30   # バズ監視間隔（分）
    buzz_threshold: float = 5.0          # バズ判定しきい値（PR倍率）
    buzz_min_views: int = 10000          # 最小再生数
    buzz_days: int = 7                   # 直近N日

    # 自動実行設定
    auto_generate_on_buzz: bool = True   # バズ検出時に自動台本生成
    max_daily_scripts: int = 3           # 1日の最大台本生成数
    target_score: int = 90               # 目標スコア

    # 通知設定
    notify_on_buzz: bool = True          # バズ検出時に通知
    notify_on_complete: bool = True      # 台本完成時に通知


class AutoScheduler:
    """
    自動実行スケジューラ

    機能:
    1. 起動時自動実行: Phase 0起動と同時にバズチェック
    2. 定期実行: 毎日/毎週の定時実行
    3. 監視トリガー: バズ動画検出で自動台本生成
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
    # バズ動画監視
    # ==========================================

    async def check_buzz_videos(self) -> List[Dict]:
        """バズ動画をチェック"""
        logger.info("🔍 Checking for buzz videos...")

        try:
            sys.path.insert(0, str(SCRIPT_DIR / "research"))
            from channel_manager import ChannelManager

            manager = ChannelManager()

            # 動画データを読み込み（なければfetch）
            videos = manager.load_videos()
            if not videos:
                logger.info("No video data. Fetching from YouTube API...")
                channels = manager.load_channels()
                if channels:
                    manager.fetch_all_channels(top_n=20, force=False)
                    videos = manager.load_videos()

            if not videos:
                logger.warning("No videos to analyze")
                return []

            # バズ動画検出
            result = manager.auto_discover_buzz(
                threshold=self.config.buzz_threshold,
                min_views=self.config.buzz_min_views,
                days=self.config.buzz_days
            )

            buzz_videos = result.get("buzz_videos", [])

            if buzz_videos:
                logger.info(f"🔥 Found {len(buzz_videos)} buzz videos!")
                for v in buzz_videos[:3]:
                    logger.info(f"  - {v['title'][:40]}... (PR: {v['performance_ratio']:.1f}x)")
            else:
                logger.info("No buzz videos found")

            return buzz_videos

        except Exception as e:
            logger.error(f"Buzz check error: {e}")
            return []

    # ==========================================
    # 台本生成
    # ==========================================

    async def generate_script_from_buzz(self, buzz_video: Dict) -> Optional[Dict]:
        """バズ動画から台本生成"""
        self._reset_daily_count()

        if self.daily_script_count >= self.config.max_daily_scripts:
            logger.warning(f"Daily limit reached ({self.config.max_daily_scripts})")
            return None

        logger.info(f"📝 Generating script from: {buzz_video['title'][:40]}...")

        try:
            from pipeline_runner import PipelineRunner

            runner = PipelineRunner()
            results = await runner.run_from_buzz(
                threshold=self.config.buzz_threshold,
                days=self.config.buzz_days,
                count=1
            )

            if results:
                self.daily_script_count += 1
                self._save_state()
                logger.info(f"✅ Script generated! (Daily count: {self.daily_script_count})")
                return asdict(results[0])

        except Exception as e:
            logger.error(f"Script generation error: {e}")

        return None

    async def run_full_pipeline(self, theme: Optional[str] = None) -> Optional[Dict]:
        """フルパイプライン実行"""
        self._reset_daily_count()

        if self.daily_script_count >= self.config.max_daily_scripts:
            logger.warning(f"Daily limit reached ({self.config.max_daily_scripts})")
            return None

        logger.info(f"🎬 Running full pipeline...")

        try:
            from pipeline_runner import PipelineRunner

            runner = PipelineRunner()

            if theme:
                result = await runner.run_pipeline(
                    theme=theme,
                    target_score=self.config.target_score
                )
            else:
                results = await runner.run_from_channels(count=1)
                result = results[0] if results else None

            if result:
                self.daily_script_count += 1
                self._save_state()
                logger.info(f"✅ Pipeline complete! Score: {result.final_score}")
                return asdict(result)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")

        return None

    # ==========================================
    # 定期実行ジョブ
    # ==========================================

    async def job_monitor_buzz(self):
        """定期バズ監視ジョブ"""
        logger.info("⏰ [Scheduled] Buzz monitoring job started")

        buzz_videos = await self.check_buzz_videos()

        if buzz_videos and self.config.auto_generate_on_buzz:
            # 最もPRが高いバズ動画で台本生成
            top_buzz = max(buzz_videos, key=lambda x: x.get("performance_ratio", 0))
            await self.generate_script_from_buzz(top_buzz)

        logger.info("⏰ [Scheduled] Buzz monitoring job completed")

    async def job_daily_pipeline(self):
        """毎日の定時パイプライン実行"""
        logger.info("⏰ [Scheduled] Daily pipeline job started")

        # まずバズチェック
        buzz_videos = await self.check_buzz_videos()

        if buzz_videos:
            # バズがあれば優先
            top_buzz = max(buzz_videos, key=lambda x: x.get("performance_ratio", 0))
            await self.generate_script_from_buzz(top_buzz)
        else:
            # なければ自動テーマ生成
            await self.run_full_pipeline()

        logger.info("⏰ [Scheduled] Daily pipeline job completed")

    async def job_weekly_analysis(self):
        """週次分析ジョブ"""
        logger.info("⏰ [Scheduled] Weekly analysis job started")

        try:
            # トレンド分析エージェントを呼び出し
            import urllib.request

            url = "http://localhost:8112/a2a/tasks/send"
            payload = {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "週次トレンドレポートを生成してください。"}]
                }
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode('utf-8'))
                logger.info("Weekly trend report generated")

        except Exception as e:
            logger.error(f"Weekly analysis error: {e}")

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
            name="Buzz Video Monitor",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Buzz monitor every {self.config.monitor_interval_minutes} minutes")

        # 毎日定時実行
        self.scheduler.add_job(
            self.job_daily_pipeline,
            CronTrigger(
                hour=self.config.daily_run_hour,
                minute=self.config.daily_run_minute
            ),
            id="daily_pipeline",
            name="Daily Pipeline",
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
            name="Weekly Analysis",
            replace_existing=True
        )
        logger.info(f"📅 Scheduled: Weekly analysis on {self.config.weekly_run_day}")

    async def start(self, run_immediately: bool = True):
        """スケジューラを開始"""
        logger.info("🚀 Starting Auto Scheduler...")

        self.running = True

        # スケジュール設定
        if self.scheduler:
            self.setup_schedules()
            self.scheduler.start()
            logger.info("✅ Scheduler started")

        # 起動時に即座にバズチェック
        if run_immediately:
            logger.info("🔥 Running initial buzz check...")
            await self.job_monitor_buzz()

        # メインループ（Ctrl+Cまで継続）
        try:
            while self.running:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def stop(self):
        """スケジューラを停止"""
        logger.info("🛑 Stopping Auto Scheduler...")
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

    parser = argparse.ArgumentParser(description="YouTube Auto Scheduler")
    parser.add_argument("command", choices=["start", "status", "run-once", "check"],
                       help="start: スケジューラ開始, status: 状態確認, run-once: 1回実行, check: バズチェックのみ")
    parser.add_argument("--no-immediate", action="store_true",
                       help="起動時の即座実行をスキップ")
    parser.add_argument("--interval", type=int, default=30,
                       help="監視間隔（分）")
    parser.add_argument("--threshold", type=float, default=5.0,
                       help="バズ判定しきい値")
    parser.add_argument("--hour", type=int, default=9,
                       help="毎日実行時刻（時）")

    args = parser.parse_args()

    config = SchedulerConfig(
        monitor_interval_minutes=args.interval,
        buzz_threshold=args.threshold,
        daily_run_hour=args.hour
    )

    scheduler = AutoScheduler(config)

    if args.command == "start":
        print("=" * 60)
        print("🤖 YouTube Auto Scheduler")
        print("=" * 60)
        print(f"  📡 Buzz monitor: every {config.monitor_interval_minutes} min")
        print(f"  📅 Daily run: {config.daily_run_hour:02d}:00")
        print(f"  🎯 Buzz threshold: PR >= {config.buzz_threshold}x")
        print(f"  📝 Max daily scripts: {config.max_daily_scripts}")
        print("=" * 60)
        print("Press Ctrl+C to stop")
        print("")

        await scheduler.start(run_immediately=not args.no_immediate)

    elif args.command == "status":
        status = scheduler.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif args.command == "run-once":
        print("🔥 Running single pipeline execution...")
        await scheduler.job_daily_pipeline()

    elif args.command == "check":
        print("🔍 Checking for buzz videos...")
        buzz = await scheduler.check_buzz_videos()
        if buzz:
            print(f"\n✅ Found {len(buzz)} buzz videos:")
            for v in buzz:
                print(f"  - {v['title'][:50]}... (PR: {v['performance_ratio']:.1f}x)")
        else:
            print("❌ No buzz videos found")


if __name__ == "__main__":
    asyncio.run(main())
